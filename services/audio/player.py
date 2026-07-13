import time
from pathlib import Path

import pygame


class AudioPlayer:
    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self._volume = 1.0
        pygame.mixer.music.set_volume(self._volume)

    def play(self, filename: str | Path):
        path = str(filename)

        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        try:
            pygame.mixer.music.unload()
        except pygame.error:
            pass

    def stop(self):
        pygame.mixer.music.stop()

    def set_volume(self, value: int):
        value = max(0, min(100, value))
        self._volume = value / 100
        pygame.mixer.music.set_volume(self._volume)