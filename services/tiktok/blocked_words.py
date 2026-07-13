class BlockedWordsManager:
    def __init__(self, config):
        self.config = config

    def get_all(self) -> list[str]:
        return list(
            self.config.get("blocked_words", [])
        )

    def add(self, word: str) -> bool:
        word = word.strip().lower()

        if not word:
            return False

        words = self.get_all()

        if word in words:
            return False

        words.append(word)
        words.sort()

        self.config.set(
            "blocked_words",
            words
        )

        return True

    def remove(self, word: str) -> bool:
        word = word.strip().lower()
        words = self.get_all()

        if word not in words:
            return False

        words.remove(word)

        self.config.set(
            "blocked_words",
            words
        )

        return True

    def clear(self):
        self.config.set(
            "blocked_words",
            []
        )

    def set_mode(self, mode: str):
        valid_modes = {
            "hide",
            "mute",
            "replace"
        }

        if mode not in valid_modes:
            raise ValueError(
                f"Modo inválido: {mode}"
            )

        self.config.set(
            "blocked_words_mode",
            mode
        )