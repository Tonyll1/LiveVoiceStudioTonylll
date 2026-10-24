"""Orquestador: crea los servicios, procesa cada evento del directo y expone acciones."""
from __future__ import annotations

import asyncio

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
from livevoice.tts.voices import PRESETS, VoiceCatalog


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
        self.giveaway = Giveaway(self.tts)
        self.poll = Poll(self.tts)
        self.goals = Goals(self.config, self.tts, self.stats)
        self.timers = Timers(self.config, self.tts)
        self.obs = OBSClient(self.config)
        self.hotkeys = Hotkeys(self.config, self._hotkey)
        self._background: list[asyncio.Task] = []
        bus.on("live.event", self.on_live_event)

    # ── Ciclo de vida ──────────────────────────────────────────────

    async def start(self):
        bus.bind_loop(asyncio.get_running_loop())
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
        await bus.emit("ws", "voices", {"count": len(self.catalog.voices)})

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

        first_message = self.stats.register(event)
        self.viewers.touch(event)
        self._award_points(event)

        if event.kind not in ("like", "join"):
            await bus.emit("ws", "event", event.to_dict())

        if event.kind == "chat":
            await self._on_chat(event, first_message)
        else:
            await self.alerts.on_event(event)
            await self.goals.on_event(event)
            await self._maybe_auto_clip(event)

    async def _on_chat(self, event: LiveEvent, first_message: bool):
        self.timers.on_chat()
        if await self.giveaway.on_chat(event) or await self.poll.on_chat(event):
            return
        if await self.commands.handle(event):
            return

        welcome = self.config.get("welcome")
        if first_message and welcome.get("enabled") and welcome.get("tts") and not event.user.is_broadcaster:
            name = clean_for_speech(event.user.name, max_length=40)
            self.tts.say(render(welcome.get("text", ""), user=name), priority=PRIORITY_EVENT)

        self.reader.read(event)

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
        elif name == "test_effect":
            try:
                self.player.play_effect(data.get("path", ""), int(data.get("volume", 100)))
            except Exception as error:
                return {"ok": False, "error": str(error)}
        else:
            return {"ok": False, "error": f"Acción desconocida: {name}"}
        return {"ok": True}

    async def _simulate(self, kind: str, data: dict):
        """Eventos de prueba para configurar alertas y overlays sin estar en directo."""
        platform = data.get("platform") or "tiktok"
        user = User(platform=platform, id="test", username="espectador_prueba",
                    display_name=data.get("user") or "Espectador de prueba", is_follower=True)
        samples = {
            "chat": dict(text=data.get("text") or "¡Hola! Me encanta el directo, saludos desde México"),
            "follow": {},
            "gift": dict(gift="Rosa", amount=5, value=5),
            "sub": dict(amount=3),
            "bits": dict(amount=100, value=100),
            "raid": dict(amount=42),
            "share": {},
            "like": dict(amount=600),
            "join": {},
        }
        await bus.emit("live.event", LiveEvent(kind=kind, platform=platform, user=user, **samples.get(kind, {})))

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
