"""Decide qué mensajes del chat se leen en voz alta y cómo."""
from __future__ import annotations

import time

from livevoice.core.models import LiveEvent
from livevoice.tts.manager import PRIORITY_CHAT, TTSManager
from livevoice.tts.text import clean_for_speech, render


PLATFORM_NAMES = {"tiktok": "TikTok", "twitch": "Twitch", "kick": "Kick", "youtube": "YouTube"}


def user_matches(event: LiveEvent, who: str, gifters: set[str] | None = None) -> bool:
    user = event.user
    if user.is_broadcaster or who == "everyone":
        return True
    if who == "followers":
        return user.is_follower or user.is_subscriber or user.is_moderator or user.platform != "tiktok"
    if who == "subscribers":
        return user.is_subscriber or user.is_moderator or user.is_vip
    if who == "moderators":
        return user.is_moderator
    if who == "gifters":
        return bool(gifters and user.key in gifters) or user.is_moderator
    return True


class ChatReader:
    def __init__(self, config, tts: TTSManager, gifters_provider):
        self.config = config
        self.tts = tts
        self.gifters_provider = gifters_provider
        self._last_read: dict[str, float] = {}

    def should_read(self, event: LiveEvent) -> tuple[bool, str]:
        settings = self.config.get("tts")
        text = event.text.strip()
        if not settings.get("enabled", True) or not event.tts_allowed:
            return False, text

        name = (event.user.username or "").lower()
        if settings.get("ignore_bots", True) and name in {bot.lower() for bot in settings.get("bots", [])}:
            return False, text
        if event.user.key in settings.get("ignored_users", []) or name in settings.get("ignored_users", []):
            return False, text

        prefix = (settings.get("prefix") or "").strip()
        if prefix:
            if not text.lower().startswith(prefix.lower()):
                return False, text
            text = text[len(prefix):].strip()
        elif settings.get("skip_commands", True) and text.startswith("!"):
            return False, text

        if not user_matches(event, settings.get("who", "everyone"), self.gifters_provider()):
            return False, text

        cooldown = int(settings.get("user_cooldown", 0) or 0)
        if cooldown:
            last = self._last_read.get(event.user.key, 0)
            if time.monotonic() - last < cooldown:
                return False, text
        return bool(text), text

    def read(self, event: LiveEvent) -> bool:
        ok, message = self.should_read(event)
        if not ok:
            return False
        settings = self.config.get("tts")
        message = clean_for_speech(
            message,
            skip_links=settings.get("skip_links", True),
            read_emojis=settings.get("read_emojis", False),
            replacements=settings.get("replacements", {}),
            max_length=int(settings.get("max_length", 200)),
        )
        if not message:
            return False

        user_name = clean_for_speech(event.user.name, read_emojis=False, max_length=40) or "Alguien"
        if settings.get("read_username", True):
            text = render(
                settings.get("template", "{user} dice: {message}"),
                user=user_name,
                message=message,
                platform=PLATFORM_NAMES.get(event.platform, event.platform),
            )
        else:
            text = message
        if settings.get("read_platform") and "{platform}" not in settings.get("template", ""):
            text = f"En {PLATFORM_NAMES.get(event.platform, event.platform)}, {text}"

        self._last_read[event.user.key] = time.monotonic()
        self.tts.say(text, priority=PRIORITY_CHAT, user_key=event.user.key, user_name=event.user.name, platform=event.platform)
        return True
