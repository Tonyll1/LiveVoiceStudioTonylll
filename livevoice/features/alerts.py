"""Alertas de follows, regalos, subs, raids, etc.: voz, sonido y animación en el overlay."""
from __future__ import annotations

from pathlib import Path

from livevoice.audio.player import AudioPlayer
from livevoice.core.bus import bus
from livevoice.core.logger import logger
from livevoice.core.models import LiveEvent
from livevoice.tts.manager import PRIORITY_ALERT, PRIORITY_EVENT, TTSManager
from livevoice.tts.text import clean_for_speech, render


TITLES = {
    "follow": "Nuevo seguidor",
    "gift": "Regalo",
    "sub": "Nueva suscripción",
    "bits": "Bits",
    "raid": "¡Raid!",
    "share": "Compartió el directo",
    "like": "Likes",
    "join": "Llegó al directo",
}


class Alerts:
    def __init__(self, config, tts: TTSManager, player: AudioPlayer):
        self.config = config
        self.tts = tts
        self.player = player
        self._like_progress = 0
        self._announced_joins: set[str] = set()

    async def on_event(self, event: LiveEvent):
        if not self.config.get("alerts.enabled", True):
            return
        settings = self.config.get(f"alerts.{event.kind}")
        if not settings or not settings.get("enabled"):
            return

        amount = event.amount
        if event.kind == "like":
            # Alerta por hitos: cada `min_amount` likes acumulados.
            step = max(1, int(settings.get("min_amount", 500)))
            before = self._like_progress // step
            self._like_progress += event.amount
            if self._like_progress // step == before:
                return
            amount = (self._like_progress // step) * step
        elif event.kind == "join":
            if event.user.key in self._announced_joins:
                return
            self._announced_joins.add(event.user.key)
        elif event.kind in ("gift", "bits"):
            if (event.value or event.amount) < int(settings.get("min_amount", 1) or 1):
                return

        user_name = clean_for_speech(event.user.name, max_length=40) or "Alguien"
        text = render(settings.get("text", ""), user=user_name, amount=amount, gift=event.gift, message=event.text)

        read_key = {"bits": "gift"}.get(event.kind, event.kind)
        if settings.get("tts") and self.config.get(f"tts.read_events.{read_key}", True) and text:
            priority = PRIORITY_ALERT if event.kind in ("gift", "sub", "raid", "bits") else PRIORITY_EVENT
            self.tts.say(text, priority=priority, user_name=event.user.name, platform=event.platform)

        sound = settings.get("sound", "")
        if sound and Path(sound).is_file():
            try:
                self.player.play_effect(sound)
            except Exception as error:
                logger.warning("No se pudo reproducir el sonido de alerta: %s", error)

        if settings.get("overlay", True):
            await bus.emit("ws", "alert", {
                "kind": event.kind,
                "platform": event.platform,
                "title": TITLES.get(event.kind, event.kind),
                "text": text,
                "user": event.user.to_dict(),
                "amount": amount,
                "gift": event.gift,
                "image": event.image,
            })
