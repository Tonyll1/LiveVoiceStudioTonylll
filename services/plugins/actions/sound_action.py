import threading
from pathlib import Path

import pygame

from core.logger import logger


class SoundAction:
    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg"}

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    def execute(self, filename: str | Path):
        path = Path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"No existe el sonido: {path}")
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError("Formato no compatible. Usa MP3, WAV u OGG.")

        threading.Thread(
            target=self._play,
            args=(path,),
            daemon=True,
            name=f"CommandSound-{path.stem}",
        ).start()

    @staticmethod
    def _play(path: Path):
        try:
            sound = pygame.mixer.Sound(str(path))
            sound.play()
        except Exception as error:
            logger.exception("Error reproduciendo %s: %s", path, error)
