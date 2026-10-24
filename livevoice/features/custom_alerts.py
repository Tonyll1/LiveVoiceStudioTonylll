"""Alertas propias: reglas del streamer con su sonido, imagen/GIF/video, frase y voz.

Ejemplos: "si alguien manda una Galaxia → sonido de explosión + GIF + voz de Ghostface",
"cuando alguien escribe 'hola papu' → sonido de risa", "follow en Kick → video corto".
"""
from __future__ import annotations

import time
from pathlib import Path

from livevoice.audio.player import AudioPlayer
from livevoice.core.bus import bus
from livevoice.core.logger import logger
from livevoice.core.models import LiveEvent
from livevoice.features.moderation import normalize
from livevoice.tts.manager import PRIORITY_ALERT, TTSManager
from livevoice.tts.text import clean_for_speech, render


TRIGGERS = {
    "gift": "Regalo",
    "follow": "Follow",
    "sub": "Suscripción",
    "bits": "Bits",
    "raid": "Raid",
    "share": "Compartir",
    "like": "Likes",
    "chat": "Palabra en el chat",
}


def media_url(path: str) -> str:
    """Las imágenes/videos subidos se sirven desde /media/<archivo>."""
    return f"/media/{Path(path).name}" if path else ""


class CustomAlerts:
    def __init__(self, config, tts: TTSManager, player: AudioPlayer):
        self.config = config
        self.tts = tts
        self.player = player
        self._last_fired: dict[str, float] = {}

    def rules(self) -> list[dict]:
        return [rule for rule in self.config.get("custom_alerts", []) if rule.get("enabled", True)]

    @staticmethod
    def matches(rule: dict, event: LiveEvent) -> bool:
        if rule.get("trigger") != event.kind:
            return False
        platforms = rule.get("platforms") or []
        if platforms and event.platform not in platforms:
            return False

        pattern = normalize(rule.get("match", ""))
        if event.kind == "chat":
            return bool(pattern) and pattern in normalize(event.text)
        if pattern:
            # Regalo concreto (Galaxia, Rose…) o variante (Tier 1, Prime, Super Chat, Miembro…).
            target = normalize(event.gift)
            if rule.get("match_mode") == "exact" and target != pattern:
                return False
            if pattern not in target:
                return False

        amount = (event.value or event.amount) if event.kind in ("gift", "bits") else event.amount
        minimum = int(rule.get("min_amount", 0) or 0)
        maximum = int(rule.get("max_amount", 0) or 0)
        return amount >= minimum and (not maximum or amount <= maximum)

    @staticmethod
    def specificity(rule: dict) -> tuple:
        """La regla más concreta gana: regalo exacto > nombre parecido > rango de valor > genérica."""
        match = 3 if rule.get("match") and rule.get("match_mode") == "exact" else 2 if rule.get("match") else 0
        return (match, bool(rule.get("platforms")), int(rule.get("min_amount", 0) or 0), bool(rule.get("max_amount")))

    async def on_event(self, event: LiveEvent) -> bool:
        """Dispara la regla más específica que encaje. Devuelve True si reemplaza la alerta normal."""
        candidates = sorted((rule for rule in self.rules() if self.matches(rule, event)), key=self.specificity, reverse=True)
        for rule in candidates:
            rule_id = str(rule.get("id") or rule.get("name"))
            cooldown = int(rule.get("cooldown", 0) or 0)
            if cooldown and time.monotonic() - self._last_fired.get(rule_id, 0) < cooldown:
                continue
            self._last_fired[rule_id] = time.monotonic()
            await self.fire(rule, event)
            return bool(rule.get("replace_default", True))
        return False

    async def fire(self, rule: dict, event: LiveEvent):
        user_name = clean_for_speech(event.user.name, max_length=40) or "Alguien"
        values = dict(user=user_name, amount=event.amount, gift=event.gift, message=event.text)

        sound = rule.get("sound", "")
        if sound:
            if Path(sound).is_file():
                try:
                    self.player.play_effect(sound, int(rule.get("volume", 100) or 100))
                except Exception as error:
                    logger.warning("Alerta propia %s: no se pudo reproducir el sonido: %s", rule.get("name"), error)
            else:
                await bus.emit("ws", "notice", {"level": "warning", "text": f"Falta el sonido de la alerta “{rule.get('name')}”."})

        spoken = render(rule.get("tts_text", ""), **values)
        if spoken:
            self.tts.say(
                spoken,
                priority=PRIORITY_ALERT,
                voice=rule.get("voice") or None,
                user_name=event.user.name,
                platform=event.platform,
            )

        if rule.get("overlay", True):
            await bus.emit("ws", "alert", {
                "kind": event.kind,
                "custom": True,
                "platform": event.platform,
                "title": rule.get("title") or rule.get("name") or "",
                "text": render(rule.get("text", ""), **values),
                "user": event.user.to_dict(),
                "amount": event.amount,
                "gift": event.gift,
                "image": event.image,
                "media": media_url(rule.get("media", "")),
                "media_type": rule.get("media_type", ""),
                "duration": float(rule.get("duration", 0) or 0),
            })
