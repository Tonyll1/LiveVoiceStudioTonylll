"""Motores de texto a voz.

Edge (online, +300 voces neuronales) es el principal. Si Microsoft cambia algo o
se cae, el gestor salta automáticamente a Google (online) y después a las voces
de Windows (sin internet), así el directo nunca se queda mudo. El resto de motores
(Windows, Piper, TikTok) están en local_engines.py.
"""
from __future__ import annotations

import asyncio
import hashlib
import urllib.parse
from pathlib import Path

import aiohttp
import edge_tts

from livevoice.core.paths import data_path


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


class TTSError(Exception):
    pass


def cache_file(*parts: object, suffix: str = ".mp3") -> Path:
    key = hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return data_path("sounds", "cache", f"{key}{suffix}")


def signed(value: int, unit: str) -> str:
    return f"{'+' if value >= 0 else ''}{int(value)}{unit}"


class EdgeEngine:
    name = "edge"
    label = "Microsoft Edge (neuronal)"

    async def synthesize(self, text: str, voice: str, rate: int = 0, pitch: int = 0) -> Path:
        target = cache_file("edge", voice, rate, pitch, text)
        if target.exists() and target.stat().st_size > 0:
            return target
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=signed(rate, "%"),
            pitch=signed(pitch, "Hz"),
        )
        temporary = target.with_suffix(".part")
        try:
            await asyncio.wait_for(communicate.save(str(temporary)), timeout=20)
        except Exception as error:
            temporary.unlink(missing_ok=True)
            raise TTSError(f"Edge TTS falló: {error}") from error
        if not temporary.exists() or temporary.stat().st_size == 0:
            temporary.unlink(missing_ok=True)
            raise TTSError("Edge TTS devolvió audio vacío.")
        temporary.replace(target)
        return target

    @staticmethod
    async def list_voices() -> list[dict]:
        return await asyncio.wait_for(edge_tts.list_voices(), timeout=20)


class GoogleEngine:
    """Voz del traductor de Google. Sin claves, un idioma por voz, máx. 200 caracteres por trozo."""

    name = "google"
    label = "Google (respaldo online)"
    URL = "https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl={lang}&q={text}"

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers={"User-Agent": USER_AGENT})
        return self._session

    @staticmethod
    def _chunks(text: str, size: int = 180) -> list[str]:
        words, chunks, current = text.split(), [], ""
        for word in words:
            if len(current) + len(word) + 1 > size and current:
                chunks.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            chunks.append(current)
        return chunks or [text[:size]]

    async def synthesize(self, text: str, lang: str = "es", rate: int = 0, pitch: int = 0) -> Path:
        target = cache_file("google", lang, text)
        if target.exists() and target.stat().st_size > 0:
            return target
        session = await self._get_session()
        audio = bytearray()
        try:
            for chunk in self._chunks(text):
                url = self.URL.format(lang=lang, text=urllib.parse.quote(chunk))
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status != 200:
                        raise TTSError(f"Google TTS respondió {response.status}")
                    audio.extend(await response.read())
        except TTSError:
            raise
        except Exception as error:
            raise TTSError(f"Google TTS falló: {error}") from error
        target.write_bytes(bytes(audio))
        return target

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


