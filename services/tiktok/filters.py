import re
import unicodedata


class MessageFilter:
    def __init__(self, config):
        self.config = config
        self.last_messages: dict[str, str] = {}

    @staticmethod
    def normalize(text: str) -> str:
        text = text.lower().strip()

        text = unicodedata.normalize("NFD", text)
        text = "".join(
            character
            for character in text
            if unicodedata.category(character) != "Mn"
        )

        return re.sub(r"\s+", " ", text)

    def process(self, user_id: str, text: str) -> tuple[bool, bool, str]:
        """
        Devuelve:
        mostrar_mensaje, leer_con_tts, texto_procesado
        """

        text = text.strip()

        if not text:
            return False, False, text

        if self.config.get("filter_spam", True):
            if not self._passes_spam_filter(user_id, text):
                return False, False, text

        blocked_words = self.config.get("blocked_words", [])
        mode = self.config.get("blocked_words_mode", "replace")

        processed_text = text
        contains_blocked_word = False

        for blocked_word in blocked_words:
            blocked_word = blocked_word.strip()

            if not blocked_word:
                continue

            pattern = re.compile(
                rf"\b{re.escape(blocked_word)}\b",
                flags=re.IGNORECASE
            )

            if pattern.search(processed_text):
                contains_blocked_word = True

                if mode == "replace":
                    processed_text = pattern.sub("***", processed_text)

        if contains_blocked_word:
            if mode == "hide":
                return False, False, processed_text

            if mode == "mute":
                return True, False, processed_text

        return True, True, processed_text

    def _passes_spam_filter(self, user_id: str, text: str) -> bool:
        if len(text) < 2:
            return False

        if len(text) > 180:
            return False

        if re.fullmatch(r"[0-9]+", text):
            return False

        if re.fullmatch(r"(.)\1{6,}", text, flags=re.DOTALL):
            return False

        if re.fullmatch(r"[😂🤣🔥❤️😍👍🙏💀😭😎\s]+", text):
            return False

        normalized = self.normalize(text)
        previous = self.last_messages.get(user_id)

        if previous == normalized:
            return False

        self.last_messages[user_id] = normalized
        return True