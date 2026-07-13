from pathlib import Path

from core.paths import data_path
import hashlib


class AudioCache:
    def __init__(self):
        self.folder = data_path("sounds", "cache")
        self.folder.mkdir(parents=True, exist_ok=True)

    def filename(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str
    ) -> Path:
        raw = f"{voice}|{rate}|{volume}|{text}"

        key = hashlib.sha1(
            raw.encode("utf-8")
        ).hexdigest()

        return self.folder / f"{key}.mp3"