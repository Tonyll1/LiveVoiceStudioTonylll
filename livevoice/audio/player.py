"""Reproducción de audio con pygame.

- La voz (TTS) usa `pygame.mixer.music`: permite pausar, saltar y controlar su volumen aparte.
- Los efectos (comandos de sonido, alertas) usan canales `Sound` que se mezclan encima.
- Se puede elegir dispositivo de salida (p. ej. "CABLE Input" de VB-Audio) para separar
  la voz del resto del audio en OBS.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from livevoice.core.logger import logger  # noqa: E402


SUPPORTED_SOUND_EXTENSIONS = {".mp3", ".wav", ".ogg"}


class AudioPlayer:
    def __init__(self, device: str = ""):
        self._lock = threading.RLock()
        self._stop_requested = threading.Event()
        self.device = ""
        self.tts_volume = 1.0
        self.sfx_volume = 0.8
        self.available = False
        self.init_device(device)

    def init_device(self, device: str = "") -> bool:
        with self._lock:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
                if device:
                    pygame.mixer.init(frequency=48000, devicename=device)
                else:
                    pygame.mixer.init(frequency=48000)
                pygame.mixer.set_num_channels(16)
                self.device = device
                self.available = True
            except pygame.error as error:
                logger.error("No se pudo abrir el dispositivo de audio '%s': %s", device, error)
                if device:
                    return self.init_device("")
                self.available = False
                return False
            pygame.mixer.music.set_volume(self.tts_volume)
            return True

    @staticmethod
    def list_devices() -> list[str]:
        try:
            from pygame._sdl2 import audio as sdl2_audio

            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return list(sdl2_audio.get_audio_device_names(False))
        except Exception as error:
            logger.warning("No se pudieron listar dispositivos de audio: %s", error)
            return []

    def set_volumes(self, tts: int | None = None, sfx: int | None = None):
        if tts is not None:
            self.tts_volume = max(0, min(100, int(tts))) / 100
            if self.available:
                pygame.mixer.music.set_volume(self.tts_volume)
        if sfx is not None:
            self.sfx_volume = max(0, min(100, int(sfx))) / 100

    def play_voice(self, filename: str | Path, is_paused=lambda: False) -> bool:
        """Reproduce y bloquea hasta terminar. Devuelve False si se saltó."""
        if not self.available:
            raise RuntimeError("No hay dispositivo de audio disponible.")
        self._stop_requested.clear()
        with self._lock:
            pygame.mixer.music.load(str(filename))
            pygame.mixer.music.set_volume(self.tts_volume)
            pygame.mixer.music.play()

        paused = False
        while True:
            if self._stop_requested.is_set():
                pygame.mixer.music.stop()
                break
            if is_paused() and not paused:
                pygame.mixer.music.pause()
                paused = True
            elif not is_paused() and paused:
                pygame.mixer.music.unpause()
                paused = False
            if not paused and not pygame.mixer.music.get_busy():
                break
            time.sleep(0.03)

        try:
            pygame.mixer.music.unload()
        except pygame.error:
            pass
        return not self._stop_requested.is_set()

    def stop_voice(self):
        self._stop_requested.set()

    def play_effect(self, filename: str | Path, volume: int | None = None):
        path = Path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"No existe el sonido: {path}")
        if path.suffix.lower() not in SUPPORTED_SOUND_EXTENSIONS:
            raise ValueError("Formato no compatible. Usa MP3, WAV u OGG.")
        if not self.available:
            raise RuntimeError("No hay dispositivo de audio disponible.")
        sound = pygame.mixer.Sound(str(path))
        level = self.sfx_volume if volume is None else max(0, min(100, volume)) / 100 * self.sfx_volume
        sound.set_volume(level)
        sound.play()

    def stop_effects(self):
        if self.available:
            pygame.mixer.stop()
