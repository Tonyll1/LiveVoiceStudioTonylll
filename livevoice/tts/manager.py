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
from livevoice.tts.ai_engines import ElevenLabsEngine, KokoroEngine
from livevoice.tts.engines import EdgeEngine, GoogleEngine, TTSError
from livevoice.tts.local_engines import PiperEngine, SapiEngine, TikTokEngine
from livevoice.tts.voices import PRESETS_BY_ID, VoiceCatalog, engine_for, migrate_voice_id, split_voice


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
    engine_used: str = field(compare=False, default="")
    voice_used: str = field(compare=False, default="")

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
            "engine_used": self.engine_used,
            "voice_used": self.voice_used,
            "fallback": bool(self.voice_used) and self.voice_used != self.voice,
        }


class TTSManager:
    def __init__(self, config: Config, player: AudioPlayer, catalog: VoiceCatalog):
        self.config = config
        self.player = player
        self.catalog = catalog
        self.engines = {
            "edge": EdgeEngine(),
            "google": GoogleEngine(),
            "tiktok": TikTokEngine(lambda: self.config.get("tts.tiktok_session_id", "")),
            "piper": PiperEngine(),
            "kokoro": KokoroEngine(),
            "elevenlabs": ElevenLabsEngine(
                lambda: self.config.get("tts.elevenlabs_key", ""),
                lambda: self.config.get("tts.elevenlabs_model", "eleven_flash_v2_5"),
            ),
            "sapi": SapiEngine(),
        }
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
        for name in ("google", "tiktok", "elevenlabs"):
            await self.engines[name].close()

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
            voice=migrate_voice_id(voice or resolved_voice),
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

    # Respaldos en orden: online primero (mejor calidad), después los que funcionan sin internet.
    FALLBACK_ORDER = ("edge", "google", "kokoro", "piper", "sapi")

    async def synthesize(self, item: SpeechItem):
        """Intenta el motor de la voz elegida y, si falla, recorre los respaldos."""
        primary = engine_for(item.voice)
        voice = self.catalog.get(item.voice)
        language = voice.language if voice else split_voice(item.voice)[1].split("-")[0].split("_")[0].lower()
        if len(language) != 2:
            language = "es"

        attempts = [primary]
        if self.config.get("tts.fallback_enabled", True):
            attempts += [name for name in self.FALLBACK_ORDER if name != primary]

        last_error: Exception | None = None
        for name in attempts:
            if name != primary and not self._engine_available(name):
                continue
            target = item.voice if name == primary else self._fallback_voice(name, language, voice.gender if voice else "")
            if target is None:
                continue
            try:
                path = await self._run_engine(name, target, item)
                self._mark(name, None)
                item.engine_used, item.voice_used = name, target
                if name != primary and item.priority >= PRIORITY_SYSTEM:
                    # Pruebas de voz: avisar que no sonó la voz elegida, en vez de cambiarla en silencio.
                    bus.emit_nowait("ws", "notice", {
                        "level": "warning",
                        "text": f"La voz {item.voice} no está disponible ({last_error}). Sonó con el respaldo: {target}.",
                    })
                return path
            except (TTSError, OSError, asyncio.TimeoutError) as error:
                last_error = error
                self._mark(name, error)
        raise TTSError(f"Ningún motor de voz respondió: {last_error}")

    async def _run_engine(self, name: str, voice_id: str, item: SpeechItem):
        kind, voice = split_voice(voice_id)
        engine = self.engines[name]
        if name == "sapi":
            return await engine.synthesize(item.text, voice, item.rate, item.pitch, kind=kind)
        return await engine.synthesize(item.text, voice, item.rate, item.pitch)

    def _fallback_voice(self, engine: str, language: str, gender: str = "") -> str | None:
        """Voz del mismo idioma (y género, si se sabe) en otro motor. None si ese motor no tiene ninguna."""
        configured = self.config.get("tts.voice", "")
        if engine == "edge":
            if engine_for(configured) == "edge" and configured.lower().startswith(language):
                return configured
            options = self.catalog.by_language(language, "edge")
            same_gender = [voice for voice in options if gender and voice.gender == gender]
            options = same_gender or options
            return options[0].id if options else "es-MX-DaliaNeural"
        if engine == "google":
            return f"google:{language}"
        options = self.catalog.by_language(language, engine)
        if engine == "sapi":
            options = options or [voice for voice in self.catalog.voices if voice.engine == "sapi"]
            # Las voces modernas (OneCore) suenan mejor que las SAPI clásicas.
            options = sorted(options, key=lambda voice: not voice.id.startswith("win:"))
        return options[0].id if options else None

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
