"""Orquestador: crea los servicios, procesa cada evento del directo y expone acciones."""
from __future__ import annotations

import asyncio
import time

from livevoice import VERSION
from livevoice.audio.player import AudioPlayer
from livevoice.core.bus import bus
from livevoice.core.config import Config
from livevoice.core.logger import logger
from livevoice.core.models import PLATFORMS, LiveEvent, User
from livevoice.core.stats import SessionStats, ViewerStore
from livevoice.features.alerts import Alerts
from livevoice.features.chat_reader import ChatReader
from livevoice.features.commands import Commands
from livevoice.features.custom_alerts import CustomAlerts
from livevoice.features.gift_catalog import GiftCatalog
from livevoice.features.dynamics import Giveaway, Goals, Poll, Timers
from livevoice.features.hotkeys import Hotkeys
from livevoice.features.moderation import Moderation
from livevoice.features.obs import OBSClient
from livevoice.platforms.kick import KickPlatform
from livevoice.platforms.tiktok import TikTokPlatform
from livevoice.platforms.twitch import TwitchPlatform
from livevoice.platforms.youtube import YouTubePlatform
from livevoice.tts.manager import PRIORITY_EVENT, PRIORITY_SYSTEM, TTSManager
from livevoice.tts.text import clean_for_speech, render
from livevoice.tts.voices import PRESETS, VoiceCatalog, migrate_voice_id


class Studio:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.catalog = VoiceCatalog()
        self.player = AudioPlayer(self.config.get("audio.output_device", ""))
        self.player.set_volumes(self.config.get("audio.tts_volume", 100), self.config.get("audio.sfx_volume", 80))
        self.stats = SessionStats()
        self.viewers = ViewerStore()
        self.tts = TTSManager(self.config, self.player, self.catalog)
        self.platforms = {
            "tiktok": TikTokPlatform(self.config),
            "twitch": TwitchPlatform(self.config),
            "kick": KickPlatform(self.config),
            "youtube": YouTubePlatform(self.config),
        }
        self.moderation = Moderation(self.config)
        self.reader = ChatReader(self.config, self.tts, lambda: set(self.stats.gifters))
        self.commands = Commands(self)
        self.alerts = Alerts(self.config, self.tts, self.player)
        self.custom_alerts = CustomAlerts(self.config, self.tts, self.player)
        self.gift_catalog = GiftCatalog()
        self.giveaway = Giveaway(self.tts)
        self.poll = Poll(self.tts)
        self.goals = Goals(self.config, self.tts, self.stats)
        self.timers = Timers(self.config, self.tts)
        self.obs = OBSClient(self.config)
        self.hotkeys = Hotkeys(self.config, self._hotkey)
        self._background: list[asyncio.Task] = []
        self._last_welcome = 0.0
        bus.on("live.event", self.on_live_event)

    # ── Ciclo de vida ──────────────────────────────────────────────

    def _migrate_retired_voices(self):
        """Voces de motores que ya no existen (StreamElements) pasan a su equivalente de Edge."""
        voice = self.config.get("tts.voice", "")
        if migrate_voice_id(voice) != voice:
            self.config.set("tts.voice", migrate_voice_id(voice))
            logger.info("Voz principal %s migrada a %s", voice, migrate_voice_id(voice))
        user_voices = self.config.get("tts.user_voices", {})
        if any(migrate_voice_id(item.get("voice", "")) != item.get("voice", "") for item in user_voices.values()):
            self.config.set("tts.user_voices", {
                key: {**item, "voice": migrate_voice_id(item.get("voice", ""))} for key, item in user_voices.items()
            })
        if "streamelements_token" in self.config.get("tts", {}):
            self.config.data["tts"].pop("streamelements_token", None)
            self.config.save()

    async def start(self):
        bus.bind_loop(asyncio.get_running_loop())
        self._migrate_retired_voices()
        self.tts.start()
        self.timers.start()
        self.hotkeys.apply()
        self._background += [
            asyncio.create_task(self._refresh_voices()),
            asyncio.create_task(self._periodic()),
        ]
        for name in PLATFORMS:
            settings = self.config.get(f"platforms.{name}")
            if settings.get("enabled") and settings.get("auto_connect") and settings.get("channel"):
                await self.platforms[name].connect(settings["channel"])
        logger.info("LiveVoice Studio %s iniciado", VERSION)

    async def shutdown(self):
        self.hotkeys.clear()
        for platform in self.platforms.values():
            await platform.disconnect()
        for task in self._background:
            task.cancel()
        await self.tts.stop()
        await self.obs.close()
        self.viewers.flush()

    async def _refresh_voices(self):
        await self.catalog.refresh()
        await self._refresh_elevenlabs(notify=False)
        await bus.emit("ws", "voices", {"count": len(self.catalog.voices)})
        if self.config.get("tts.voice", "").startswith("kokoro:"):
            await self.tts.engines["kokoro"].warm_up()

    async def _refresh_elevenlabs(self, notify: bool = True) -> dict:
        try:
            voices = await self.tts.engines["elevenlabs"].list_voices()
        except Exception as error:
            if notify:
                return {"ok": False, "error": str(error)}
            logger.warning("No se pudieron leer las voces de ElevenLabs: %s", error)
            return {"ok": False}
        self.catalog.set_elevenlabs(voices)
        if notify:
            await bus.emit("ws", "voices", {"count": len(self.catalog.voices)})
        return {"ok": True, "count": len(voices)}

    async def _download_kokoro(self):
        async def progress(percent: int):
            await bus.emit("ws", "download", {"key": "kokoro", "percent": percent})

        try:
            await progress(0)
            await self.tts.engines["kokoro"].download(progress)
            self.catalog.reload_local()
            await bus.emit("ws", "download", {"key": "kokoro", "percent": 100, "done": True})
            await bus.emit("ws", "voices", {"count": len(self.catalog.voices)})
            await bus.emit("ws", "notice", {"level": "success", "text": "Voces Kokoro listas: IA que funciona sin internet."})
            await self.tts.engines["kokoro"].warm_up()
        except Exception as error:
            logger.warning("Descarga de Kokoro falló: %s", error)
            await bus.emit("ws", "download", {"key": "kokoro", "error": str(error)})
            await bus.emit("ws", "notice", {"level": "error", "text": f"No se pudo descargar Kokoro: {error}"})

    async def _periodic(self):
        while True:
            await asyncio.sleep(5)
            await bus.emit("ws", "stats", self.stats.to_dict())
            self.viewers.flush()

    def _hotkey(self, action: str):
        """Llamado desde el hilo de `keyboard`."""
        if bus.loop:
            asyncio.run_coroutine_threadsafe(self.action(action, {}), bus.loop)

    # ── Proceso de eventos ─────────────────────────────────────────

    async def on_live_event(self, event: LiveEvent):
        if event.kind == "chat" and not self.moderation.check(event):
            return

        # ¿Es la primera vez que esta persona escribe en tu canal (en cualquier sesión)?
        first_ever = event.kind == "chat" and not (self.viewers.get(event.user.key) or {}).get("messages", 0)
        first_message = self.stats.register(event)
        self.gift_catalog.record(event)
        self.viewers.touch(event)
        self._award_points(event)

        if event.kind not in ("like", "join"):
            await bus.emit("ws", "event", event.to_dict())

        if event.kind == "chat":
            await self._on_chat(event, first_message, first_ever)
        else:
            # Una alerta propia que encaje puede reemplazar a la alerta normal de ese evento.
            if not await self.custom_alerts.on_event(event):
                await self.alerts.on_event(event)
            await self.goals.on_event(event)
            await self._maybe_auto_clip(event)

    async def _on_chat(self, event: LiveEvent, first_message: bool, first_ever: bool = False):
        self.timers.on_chat()
        await self.custom_alerts.on_event(event)
        if await self.giveaway.on_chat(event) or await self.poll.on_chat(event):
            return
        if await self.commands.handle(event):
            return

        if first_message:
            self._welcome(event, first_ever)

        self.reader.read(event)

    def _welcome(self, event: LiveEvent, first_ever: bool):
        """Saluda por voz según el modo elegido, sin saturar la cola en directos con mucho chat."""
        welcome = self.config.get("welcome")
        if not welcome.get("enabled") or not welcome.get("tts") or event.user.is_broadcaster:
            return
        mode = welcome.get("mode", "new")
        if first_ever:
            template = welcome.get("text", "")
        elif mode == "session":
            template = welcome.get("text_back", "")
        else:
            return
        if not template:
            return
        cooldown = int(welcome.get("cooldown", 0) or 0)
        if cooldown and time.monotonic() - self._last_welcome < cooldown:
            return
        if len(self.tts.pending) >= int(welcome.get("max_queue", 3) or 99):
            return
        self._last_welcome = time.monotonic()
        name = clean_for_speech(event.user.name, max_length=40)
        self.tts.say(render(template, user=name), priority=PRIORITY_EVENT)

    def _award_points(self, event: LiveEvent):
        points = self.config.get("points")
        if not points.get("enabled", True):
            return
        amount = {
            "chat": points.get("per_message", 1),
            "follow": points.get("per_follow", 20),
            "share": points.get("per_share", 10),
            "sub": points.get("per_sub", 50),
            "gift": (event.value or event.amount) * points.get("per_gift_coin", 5),
            "bits": event.amount * points.get("per_gift_coin", 5) // 10,
        }.get(event.kind, 0)
        if event.kind == "chat":
            viewer = self.viewers.get(event.user.key)
            if viewer:
                viewer["messages"] = viewer.get("messages", 0) + 1
        self.viewers.add_points(event.user.key, int(amount))

    async def _maybe_auto_clip(self, event: LiveEvent):
        threshold = int(self.config.get("obs.auto_clip_min_gift", 0) or 0)
        if threshold and event.kind in ("gift", "bits") and (event.value or event.amount) >= threshold:
            await self.obs.clip(f"regalo de {event.user.name}: {event.amount} {event.gift}")

    # ── Acciones (API, atajos, panel) ──────────────────────────────

    async def action(self, name: str, data: dict) -> dict:
        data = data or {}
        if name == "toggle_mute":
            self.tts.toggle_mute()
        elif name == "mute":
            self.tts.set_muted(bool(data.get("value", True)))
        elif name == "skip":
            self.tts.skip()
        elif name == "clear_queue":
            self.tts.clear()
        elif name == "pause":
            self.tts.toggle_pause()
        elif name == "remove_queue_item":
            self.tts.remove(str(data.get("id", "")))
        elif name == "clip":
            return await self.obs.clip(data.get("reason") or "atajo / panel")
        elif name == "say":
            self.tts.say(str(data.get("text", "")), priority=PRIORITY_SYSTEM, voice=data.get("voice") or None, force=True)
        elif name == "preview_voice":
            voice = data.get("voice") or self.config.get("tts.voice")
            preset = next((p for p in PRESETS if p["id"] == data.get("preset")), PRESETS[0])
            item = self.tts.say(
                data.get("text") or "Hola, así sueno en tu directo. ¡Gracias por el follow!",
                priority=PRIORITY_SYSTEM, voice=voice, force=True,
            )
            if item:
                item.rate = int(data.get("rate", self.config.get("tts.rate", 0))) + preset["rate"]
                item.pitch = int(data.get("pitch", self.config.get("tts.pitch", 0))) + preset["pitch"]
        elif name == "connect":
            platform = data.get("platform", "")
            channel = data.get("channel") or self.config.get(f"platforms.{platform}.channel", "")
            if platform not in self.platforms:
                return {"ok": False, "error": "Plataforma desconocida"}
            self.config.set(f"platforms.{platform}.channel", channel)
            await self.platforms[platform].connect(channel)
        elif name == "disconnect":
            platform = self.platforms.get(data.get("platform", ""))
            if platform:
                await platform.disconnect()
        elif name == "simulate":
            await self._simulate(data.get("kind", "chat"), data)
        elif name == "giveaway_start":
            await self.giveaway.start(data.get("keyword", "!sorteo"), data.get("prize", ""), data.get("who", "everyone"))
        elif name == "giveaway_stop":
            await self.giveaway.stop()
        elif name == "giveaway_draw":
            winner = await self.giveaway.draw()
            return {"ok": True, "winner": winner}
        elif name == "giveaway_reset":
            self.giveaway.reset()
            await bus.emit("ws", "giveaway", self.giveaway.state())
        elif name == "poll_start":
            await self.poll.start(data.get("question", ""), data.get("options", []), int(data.get("duration", 60)))
        elif name == "poll_finish":
            await self.poll.finish()
        elif name == "goal_reset":
            self.goals.reset(data.get("goal", "likes"))
            await self.goals.publish()
        elif name == "reset_session":
            self.stats.reset()
            self.goals.offsets = dict.fromkeys(self.goals.offsets, 0)
            self.goals.celebrated.clear()
            await self.goals.publish()
        elif name == "set_audio_device":
            device = data.get("device", "")
            self.config.set("audio.output_device", device)
            ok = await asyncio.to_thread(self.player.init_device, device)
            return {"ok": ok}
        elif name == "obs_test":
            return await self.obs.test()
        elif name == "reload_hotkeys":
            self.hotkeys.apply()
            return {"ok": True, **self.hotkeys.state()}
        elif name == "refresh_voices":
            await self._refresh_voices()
        elif name == "piper_catalog":
            try:
                catalog = await self.tts.engines["piper"].fetch_catalog()
            except Exception as error:
                return {"ok": False, "error": f"No se pudo leer el catálogo de Piper: {error}"}
            installed = {item["key"] for item in self.tts.engines["piper"].installed()}
            return {"ok": True, "voices": [{**entry, "installed": entry["key"] in installed} for entry in catalog]}
        elif name == "piper_download":
            entry = data.get("entry") or {}
            if not entry.get("key") or not entry.get("path"):
                return {"ok": False, "error": "Voz Piper inválida"}
            asyncio.create_task(self._download_piper(entry))
        elif name == "kokoro_download":
            asyncio.create_task(self._download_kokoro())
        elif name == "kokoro_delete":
            self.tts.engines["kokoro"].delete()
            self.catalog.reload_local()
            await bus.emit("ws", "voices", {"count": len(self.catalog.voices)})
        elif name == "kokoro_status":
            engine = self.tts.engines["kokoro"]
            from livevoice.tts.ai_engines import KOKORO_SIZE_MB, kokoro_available

            return {"ok": True, "installed": engine.installed, "available": kokoro_available(), "size_mb": KOKORO_SIZE_MB}
        elif name == "elevenlabs_refresh":
            return await self._refresh_elevenlabs()
        elif name == "piper_delete":
            self.tts.engines["piper"].delete(str(data.get("key", "")))
            self.catalog.reload_piper()
            await bus.emit("ws", "voices", {"count": len(self.catalog.voices)})
        elif name == "simulate_burst":
            asyncio.create_task(self._simulate_burst(data.get("kind", "chat"), int(data.get("count", 8))))
        elif name == "gift_catalog":
            gifts = await self.gift_catalog.for_platform(data.get("platform", "tiktok"), bool(data.get("refresh")))
            return {"ok": True, "gifts": gifts}
        elif name == "custom_alert_test":
            rules = self.config.get("custom_alerts", [])
            rule = next((item for item in rules if str(item.get("id")) == str(data.get("id"))), None)
            if rule is None:
                return {"ok": False, "error": "Alerta no encontrada"}
            user = User(platform=data.get("platform") or "tiktok", username="espectador_prueba", display_name="Espectador de prueba")
            platform = (rule.get("platforms") or [data.get("platform") or "tiktok"])[0]
            user.platform = platform
            minimum = max(1, int(rule.get("min_amount", 1) or 1))
            sample = LiveEvent(kind=rule.get("trigger", "gift"), platform=platform, user=user,
                               text=rule.get("match", ""), gift=rule.get("match") or "Rose",
                               amount=minimum, value=minimum, image=rule.get("gift_image", ""))
            await self.custom_alerts.fire(rule, sample)
        elif name == "test_effect":
            try:
                self.player.play_effect(data.get("path", ""), int(data.get("volume", 100)))
            except Exception as error:
                return {"ok": False, "error": str(error)}
        else:
            return {"ok": False, "error": f"Acción desconocida: {name}"}
        return {"ok": True}

    async def _download_piper(self, entry: dict):
        key = entry["key"]

        async def progress(percent: int):
            await bus.emit("ws", "download", {"key": key, "percent": percent})

        try:
            await progress(0)
            await self.tts.engines["piper"].download(entry, progress)
            self.catalog.reload_piper()
            await bus.emit("ws", "download", {"key": key, "percent": 100, "done": True})
            await bus.emit("ws", "voices", {"count": len(self.catalog.voices)})
            await bus.emit("ws", "notice", {"level": "success", "text": f"Voz Piper {key} lista. Funciona sin internet."})
        except Exception as error:
            logger.warning("Descarga Piper %s falló: %s", key, error)
            await bus.emit("ws", "download", {"key": key, "error": str(error)})
            await bus.emit("ws", "notice", {"level": "error", "text": f"No se pudo descargar {key}: {error}"})

    async def _simulate_burst(self, kind: str, count: int):
        """Varios eventos seguidos de distintos espectadores, para ver el directo "lleno"."""
        names = ["Ana", "gamer_pro", "Luis MX", "SofiStreams", "el_pepe", "Carla", "NoobMaster", "Vale"]
        messages = ["¡Hola!", "Qué buen directo", "jajaja", "saludos desde Chile", "¿Qué juego es?", "🔥🔥🔥",
                    "eres el mejor", "primera vez por aquí", "!dado", "!voz ardilla"]
        gifts = [("Rose", 1), ("TikTok", 1), ("Heart Me", 1), ("Doughnut", 30), ("Galaxy", 1000)]
        platforms = ["tiktok", "twitch", "kick", "youtube"]
        for index in range(max(1, min(count, 30))):
            name = names[index % len(names)]
            payload = {"user": name, "platform": platforms[index % len(platforms)]}
            if kind == "chat":
                payload["text"] = messages[index % len(messages)]
            elif kind == "gift":
                gift, value = gifts[index % len(gifts)]
                payload.update(gift=gift, amount=1 + index % 3, value=value * (1 + index % 3), platform="tiktok")
            await self._simulate(kind, payload)
            await asyncio.sleep(0.4)

    async def _simulate(self, kind: str, data: dict):
        """Eventos de prueba para configurar alertas y overlays sin estar en directo."""
        platform = data.get("platform") or "tiktok"
        display = data.get("user") or "Espectador de prueba"
        user = User(
            platform=platform,
            id="test",
            username=display.lower().replace(" ", "_"),
            display_name=display,
            is_follower=True,
            is_moderator=bool(data.get("is_moderator")),
            is_subscriber=bool(data.get("is_subscriber")),
            avatar=data.get("avatar", ""),
        )
        samples = {
            "chat": dict(text=data.get("text") or "¡Hola! Me encanta el directo, saludos desde México"),
            "follow": {},
            "gift": dict(gift="Rose", amount=5, value=5),
            "sub": dict(amount=3),
            "bits": dict(amount=100, value=100),
            "raid": dict(amount=42),
            "share": {},
            "like": dict(amount=600),
            "join": {},
        }
        values = dict(samples.get(kind, {}))
        for field in ("text", "gift"):
            if data.get(field):
                values[field] = str(data[field])
        for field in ("amount", "value"):
            if data.get(field) not in (None, ""):
                values[field] = int(data[field])
        await bus.emit("live.event", LiveEvent(kind=kind, platform=platform, user=user, **values))

    # ── Estado completo para el panel ──────────────────────────────

    def state(self) -> dict:
        return {
            "version": VERSION,
            "config": self.config.snapshot(),
            "platforms": {name: platform.info() for name, platform in self.platforms.items()},
            "tts": self.tts.state(),
            "stats": self.stats.to_dict(),
            "recent": list(self.stats.recent)[-120:],
            "giveaway": self.giveaway.state(),
            "poll": self.poll.state(),
            "goals": self.goals.state(),
            "hotkeys": self.hotkeys.state(),
            "obs": {"connected": self.obs.connected, "error": self.obs.last_error, "clips": self.obs.clips_taken},
            "audio": {"device": self.player.device, "available": self.player.available},
            "presets": PRESETS,
        }
