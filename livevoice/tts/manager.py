"""Cola de voz con prioridades, controles en vivo y respaldo automático entre motores."""
from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field

from livevoice.audio.player import AudioPlayer
from livevoice.core.bus import bus
from livevoice.core.config import Config
from livevoice.core.logger import logger
from livevoice.tts.engines import EdgeEngine, GoogleEngine, SapiEngine, TTSError
from livevoice.tts.voices import PRESETS_BY_ID, VoiceCatalog, engine_for


PRIORITY_CHAT = 10
PRIORITY_EVENT = 50
PRIORITY_ALERT = 80
PRIORITY_SYSTEM = 100

# Tras un fallo, un motor se considera caído este tiempo antes de reintentarlo.
ENGINE_COOLDOWN_SECONDS = 60


@dataclass(order=True)
class SpeechItem:
    sort_key: tuple = field(init=False, repr=False)
    priority: int
    seq: int
    text: str = field(compare=False)
    voice: str = field(compare=False)
    rate: int = field(compare=False, default=0)
    pitch: int = field(compare=False, default=0)
    user: str = field(compare=False, default="")
    platform: str = field(compare=False, default="")
    created: float = field(compare=False, default_factory=time.time)

    def __post_init__(self):
        self.sort_key = (-self.priority, self.seq)

    @property
    def id(self) -> str:
        return str(self.seq)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "voice": self.voice,
            "user": self.user,
            "platform": self.platform,
            "priority": self.priority,
        }


class TTSManager:
    def __init__(self, config: Config, player: AudioPlayer, catalog: VoiceCatalog):
        self.config = config
        self.player = player
        self.catalog = catalog
        self.engines = {"edge": EdgeEngine(), "google": GoogleEngine(), "sapi": SapiEngine()}
        self.engine_status: dict[str, dict] = {
            name: {"ok": True, "error": "", "failed_at": 0.0} for name in self.engines
        }
        self.pending: list[SpeechItem] = []
        self.current: SpeechItem | None = None
        self.muted = False
        self.paused = False
        self._seq = itertools.count(1)
        self._wakeup = asyncio.Event()
        self._generation = 0
        self._task: asyncio.Task | None = None

    # ── Ciclo de vida ──────────────────────────────────────────────

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._worker(), name="tts-worker")

    async def stop(self):
        if self._task:
            self._task.cancel()
        self.player.stop_voice()
        await self.engines["google"].close()

    # ── API pública ────────────────────────────────────────────────

    def voice_for_user(self, user_key: str) -> tuple[str, int, int]:
        """Voz, velocidad y tono que corresponden a un espectador."""
        tts = self.config.get("tts")
        voice, rate, pitch = tts["voice"], int(tts["rate"]), int(tts["pitch"])

        if user_key and tts.get("random_voice_per_user"):
            voice = self.catalog.random_for(user_key, tts.get("random_voice_language", "es")) or voice

        custom = tts.get("user_voices", {}).get(user_key) if user_key else None
        if custom:
            voice = custom.get("voice") or voice
            preset = PRESETS_BY_ID.get(custom.get("preset", ""))
            if preset:
                rate, pitch = rate + preset["rate"], pitch + preset["pitch"]
        return voice, rate, pitch

    def say(
        self,
        text: str,
        *,
        priority: int = PRIORITY_CHAT,
        user_key: str = "",
        user_name: str = "",
        platform: str = "",
        voice: str | None = None,
        force: bool = False,
    ) -> SpeechItem | None:
        text = (text or "").strip()
        if not text:
            return None
        if not force and (self.muted or not self.config.get("tts.enabled", True)):
            return None

        resolved_voice, rate, pitch = self.voice_for_user(user_key)
        item = SpeechItem(
            priority=priority,
            seq=next(self._seq),
            text=text,
            voice=voice or resolved_voice,
            rate=rate,
            pitch=pitch,
            user=user_name,
            platform=platform,
        )
        self.pending.append(item)
        self.pending.sort()
        self._trim_queue()
        self._wakeup.set()
        self._publish_queue()
        return item

    def skip(self):
        self.player.stop_voice()

    def clear(self):
        self._generation += 1
        self.pending.clear()
        self.player.stop_voice()
        self._publish_queue()

    def remove(self, item_id: str):
        self.pending = [item for item in self.pending if item.id != item_id]
        self._publish_queue()

    def set_muted(self, muted: bool):
        self.muted = bool(muted)
        if self.muted:
            self.clear()
        self._publish_state()

    def toggle_mute(self):
        self.set_muted(not self.muted)

    def set_paused(self, paused: bool):
        self.paused = bool(paused)
        self._wakeup.set()
        self._publish_state()

    def toggle_pause(self):
        self.set_paused(not self.paused)

    def state(self) -> dict:
        return {
            "muted": self.muted,
            "paused": self.paused,
            "current": self.current.to_dict() if self.current else None,
            "queue": [item.to_dict() for item in self.pending[:50]],
            "queue_size": len(self.pending),
            "engines": self.engine_status,
        }

    # ── Internos ───────────────────────────────────────────────────

    def _trim_queue(self):
        limit = max(1, int(self.config.get("tts.max_queue", 25)))
        while len(self.pending) > limit:
            # Descarta el mensaje de chat más viejo; nunca descarta alertas.
            chats = [item for item in self.pending if item.priority <= PRIORITY_CHAT]
            if not chats:
                break
            self.pending.remove(min(chats, key=lambda item: item.seq))

    def _publish_queue(self):
        bus.emit_nowait("ws", "tts.state", self.state())

    def _publish_state(self):
        self._publish_queue()

    def _engine_available(self, name: str) -> bool:
        status = self.engine_status[name]
        return status["ok"] or time.time() - status["failed_at"] > ENGINE_COOLDOWN_SECONDS

    def _mark(self, name: str, error: Exception | None):
        status = self.engine_status[name]
        was_ok = status["ok"]
        if error is None:
            status.update(ok=True, error="")
            if not was_ok:
                bus.emit_nowait("ws", "notice", {"level": "success", "text": f"El motor de voz {name} volvió a funcionar."})
        else:
            status.update(ok=False, error=str(error)[:200], failed_at=time.time())
            if was_ok:
                logger.warning("Motor de voz %s falló: %s", name, error)
                hint = " Ejecuta update.bat para actualizar las voces." if name == "edge" and "403" in str(error) else ""
                bus.emit_nowait("ws", "notice", {
                    "level": "warning",
                    "text": f"El motor {name} falló, usando respaldo automático.{hint} ({str(error)[:80]})",
                })

    async def synthesize(self, item: SpeechItem):
        """Intenta el motor de la voz elegida y, si falla, recorre los respaldos."""
        primary = engine_for(item.voice)
        voice = self.catalog.get(item.voice)
        language = voice.language if voice else item.voice.split("-")[0].replace("google:", "").replace("sapi:", "") or "es"
        if len(language) != 2:
            language = "es"

        attempts = [primary]
        if self.config.get("tts.fallback_enabled", True):
            attempts += [name for name in ("edge", "google", "sapi") if name != primary]

        last_error: Exception | None = None
        for name in attempts:
            if name != primary and not self._engine_available(name):
                continue
            try:
                if name == "edge":
                    edge_voice = item.voice if primary == "edge" else self._edge_voice_for(language)
                    path = await self.engines["edge"].synthesize(item.text, edge_voice, item.rate, item.pitch)
                elif name == "google":
                    lang = item.voice.split(":", 1)[1] if primary == "google" else language
                    path = await self.engines["google"].synthesize(item.text, lang)
                else:
                    sapi_voice = item.voice.split(":", 1)[1] if primary == "sapi" else ""
                    path = await self.engines["sapi"].synthesize(item.text, sapi_voice, item.rate)
                self._mark(name, None)
                return path
            except (TTSError, OSError, asyncio.TimeoutError) as error:
                last_error = error
                self._mark(name, error)
        raise TTSError(f"Ningún motor de voz respondió: {last_error}")

    def _edge_voice_for(self, language: str) -> str:
        configured = self.config.get("tts.voice", "")
        if engine_for(configured) == "edge" and configured.lower().startswith(language):
            return configured
        options = self.catalog.by_language(language)
        return options[0].id if options else "es-MX-DaliaNeural"

    async def _worker(self):
        prepared: tuple[SpeechItem, asyncio.Task, int] | None = None
        while True:
            try:
                if prepared is None:
                    while not self.pending:
                        self._wakeup.clear()
                        await self._wakeup.wait()
                    item = self.pending.pop(0)
                    prepared = (item, asyncio.create_task(self.synthesize(item)), self._generation)

                item, synth_task, generation = prepared
                prepared = None
                try:
                    path = await synth_task
                except Exception as error:
                    logger.error("No se pudo generar la voz: %s", error)
                    bus.emit_nowait("ws", "notice", {"level": "error", "text": "No se pudo generar la voz de un mensaje."})
                    continue

                while self.paused:
                    await asyncio.sleep(0.1)

                if generation != self._generation or (self.muted and item.priority < PRIORITY_SYSTEM):
                    continue

                # Sintetiza el siguiente mientras suena el actual para no dejar silencios.
                if self.pending:
                    next_item = self.pending.pop(0)
                    prepared = (next_item, asyncio.create_task(self.synthesize(next_item)), self._generation)

                self.current = item
                self._publish_queue()
                await bus.emit("ws", "tts.speaking", {**item.to_dict(), "speaking": True})
                try:
                    await asyncio.to_thread(self.player.play_voice, path, lambda: self.paused)
                except Exception as error:
                    logger.error("Error reproduciendo voz: %s", error)
                    bus.emit_nowait("ws", "notice", {"level": "error", "text": f"Error de audio: {error}"})
                    await asyncio.sleep(1)
                finally:
                    self.current = None
                    await bus.emit("ws", "tts.speaking", {**item.to_dict(), "speaking": False})
                    self._publish_queue()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Fallo inesperado en el worker de voz")
                await asyncio.sleep(1)
