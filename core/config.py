import json
from core.paths import data_path


CONFIG_FILE = data_path("config.json")


DEFAULT_CONFIG = {
    "engine": "edge",
    "voice": "es-MX-DaliaNeural",
    "random_voice": False,
    "random_voice_language": "es",
    "random_voice_locale": "Todos",
    "random_voice_gender": "Todos",
    "rate": "+0%",
    "volume": "+0%",
    "username": "",
    "platform": "TikTok",
    "twitch_channel": "",
    "filter_spam": True,
    "filter_emoji_spam": True,
    "filter_ascii_art": True,
    "read_username": True,
    "read_comments": True,
    "read_gifts": True,
    "read_followers": True
}


class Config:
    def __init__(self):
        if not CONFIG_FILE.exists():
            self.data = DEFAULT_CONFIG.copy()
            self.save()
        else:
            self.data = self.load()
            self.ensure_defaults()

    def load(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return DEFAULT_CONFIG.copy()

    def ensure_defaults(self):
        changed = False

        for key, value in DEFAULT_CONFIG.items():
            if key not in self.data:
                self.data[key] = value
                changed = True

        if changed:
            self.save()

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(
                self.data,
                file,
                indent=4,
                ensure_ascii=False
            )

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


config = Config()