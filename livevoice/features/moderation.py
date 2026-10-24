"""Filtro antispam y palabras bloqueadas."""
from __future__ import annotations

import re
import unicodedata

from livevoice.core.models import LiveEvent


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().strip())
    text = "".join(character for character in text if unicodedata.category(character) != "Mn")
    return re.sub(r"\s+", " ", text)


class Moderation:
    def __init__(self, config):
        self.config = config
        self._last_by_user: dict[str, str] = {}

    def check(self, event: LiveEvent) -> bool:
        """Devuelve False si el mensaje debe ocultarse. Puede marcarlo como no leíble o censurarlo."""
        text = event.text.strip()
        if not text:
            return False

        settings = self.config.get("moderation")
        if settings.get("filter_spam", True) and not self._passes_spam(event.user.key, text):
            event.tts_allowed = False

        mode = settings.get("blocked_mode", "replace")
        found = False
        for word in settings.get("blocked_words", []):
            word = word.strip()
            if not word:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(word)}(?!\w)", re.IGNORECASE)
            if pattern.search(event.text) or pattern.search(normalize(event.text)):
                found = True
                if mode == "replace":
                    event.text = pattern.sub("***", event.text)

        if found:
            if mode == "hide":
                return False
            if mode == "mute":
                event.tts_allowed = False
        return True

    def _passes_spam(self, user_key: str, text: str) -> bool:
        if len(text) < 2 or len(text) > 300:
            return False
        if re.fullmatch(r"[\d\s]+", text) and len(text) > 2:
            return False
        if re.fullmatch(r"(.)\1{5,}", text, flags=re.DOTALL):
            return False
        letters = sum(character.isalpha() for character in text)
        if letters == 0 and len(text) > 3:
            return False
        normalized = normalize(text)
        if self._last_by_user.get(user_key) == normalized:
            return False
        self._last_by_user[user_key] = normalized
        if len(self._last_by_user) > 5000:
            self._last_by_user.clear()
        return True
