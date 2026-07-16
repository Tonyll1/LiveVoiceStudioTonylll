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

        if self.config.get("filter_emoji_spam", True):
            if self._is_emoji_spam(text):
                return False, False, text

        if self.config.get("filter_ascii_art", True):
            if self._is_ascii_art_spam(text):
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

        normalized = self.normalize(text)
        previous = self.last_messages.get(user_id)

        if previous == normalized:
            return False

        self.last_messages[user_id] = normalized
        return True

    @classmethod
    def _is_emoji_spam(cls, text: str) -> bool:
        """Detecta mensajes dominados por emojis sin bloquear usos normales.

        Se bloquea cuando hay cuatro o más emojis y no existe texto real, o
        cuando los emojis representan al menos el 70 % de los elementos del
        mensaje. Un emoji aislado o acompañado de una frase sí pasa.
        """
        visible = [character for character in text if not character.isspace()]
        if not visible:
            return False

        emoji_count = sum(cls._is_emoji_character(ch) for ch in visible)
        if emoji_count < 4:
            return False

        text_characters = sum(
            character.isalnum()
            for character in visible
        )

        if text_characters == 0:
            return True

        return emoji_count / len(visible) >= 0.70


    @staticmethod
    def _is_ascii_art_spam(text: str) -> bool:
        """Detecta dibujos hechos principalmente con símbolos.

        La heurística exige una cantidad mínima de caracteres y una proporción
        alta de símbolos para no bloquear mensajes normales con puntuación,
        emoticonos cortos o frases como ``¡hola!!!``. También contempla bloques
        Unicode, caracteres braille y arte de caja usado frecuentemente en chat.
        """
        visible = [character for character in text if not character.isspace()]
        if len(visible) < 8:
            return False

        alphanumeric_count = sum(character.isalnum() for character in visible)
        symbol_count = len(visible) - alphanumeric_count
        symbol_ratio = symbol_count / len(visible)

        art_characters = sum(
            (
                0x2500 <= ord(character) <= 0x259F  # cajas y bloques
                or 0x2800 <= ord(character) <= 0x28FF  # braille
                or character in r"/\|_-=+*~^`'.,:;()[]{}<>"
            )
            for character in visible
        )

        # Dibujo puro o casi puro: ┏━━━━┓, ⣿⣿⣿⣿, /\_/\, etc.
        if alphanumeric_count <= 2 and symbol_ratio >= 0.75:
            return True

        # Arte acompañado por unas pocas letras, pero dominado por trazos.
        return (
            len(visible) >= 12
            and alphanumeric_count <= 5
            and symbol_ratio >= 0.70
            and art_characters / len(visible) >= 0.55
        )

    @staticmethod
    def _is_emoji_character(character: str) -> bool:
        codepoint = ord(character)

        # Rangos principales de pictogramas, símbolos emoji y banderas.
        if (
            0x1F000 <= codepoint <= 0x1FAFF
            or 0x2600 <= codepoint <= 0x27BF
            or 0x2300 <= codepoint <= 0x23FF
            or 0x2B00 <= codepoint <= 0x2BFF
            or 0x1F1E6 <= codepoint <= 0x1F1FF
        ):
            return True

        # Modificadores usados por emojis compuestos.
        return (
            codepoint in {0x200D, 0xFE0F, 0x20E3}
            or 0x1F3FB <= codepoint <= 0x1F3FF
        )
