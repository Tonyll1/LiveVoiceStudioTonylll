"""Voces de IA.

- KokoroEngine: IA local (sin internet) de alta calidad. Modelo de ~350 MB que se descarga una vez.
  Voces en español (Alex, Dora, Santa), inglés, portugués, francés, italiano e hindi.
- ElevenLabsEngine: IA en la nube con la clave del usuario (plan gratuito con caracteres al mes).
  Incluye las voces que el usuario clone en elevenlabs.io.
"""
from __future__ import annotations

import asyncio
import wave
from pathlib import Path

import aiohttp

from livevoice.core.paths import data_path
from livevoice.tts.engines import USER_AGENT, TTSError, cache_file


# ── Kokoro ─────────────────────────────────────────────────────────────────

KOKORO_FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
KOKORO_SIZE_MB = 355

# Prefijo de la voz -> (idioma de Kokoro, locale). Solo idiomas que funcionan con espeak.
KOKORO_LANGS = {
    "a": ("en-us", "en-US"), "b": ("en-gb", "en-GB"), "e": ("es", "es-ES"), "f": ("fr-fr", "fr-FR"),
    "i": ("it", "it-IT"), "p": ("pt-br", "pt-BR"), "h": ("hi", "hi-IN"),
}


def kokoro_available() -> bool:
    try:
        import kokoro_onnx  # noqa: F401
    except Exception as error:
        from livevoice.core.logger import logger

        logger.warning("Kokoro no se pudo cargar: %r", error)
        return False
    return True


class KokoroEngine:
    name = "kokoro"
    label = "Kokoro IA (sin internet)"

    def __init__(self):
        self.folder = data_path("voices", "kokoro", "x").parent
        self._model = None
        self._lock = asyncio.Lock()

    @property
    def installed(self) -> bool:
        return all((self.folder / name).exists() for name in KOKORO_FILES)

    def voices(self) -> list[dict]:
        """Voces del modelo instalado (vacío si no está descargado)."""
        if not self.installed:
            return []
        try:
            import numpy as np

            names = sorted(np.load(self.folder / "voices-v1.0.bin").files)
        except Exception:
            return []
        result = []
        for name in names:
            lang = KOKORO_LANGS.get(name[:1])
            if not lang or len(name) < 3:
                continue
            result.append({
                "key": name,
                "name": name[3:].replace("_", " ").title(),
                "locale": lang[1],
                "gender": "Female" if name[1] == "f" else "Male",
            })
        return result

    def _load(self):
        if self._model is None:
            from kokoro_onnx import Kokoro

            self._model = Kokoro(str(self.folder / "kokoro-v1.0.onnx"), str(self.folder / "voices-v1.0.bin"))
        return self._model

    def _render(self, text: str, voice: str, rate: int, target: Path):
        import numpy as np

        model = self._load()
        lang = KOKORO_LANGS.get(voice[:1], ("es", ""))[0]
        speed = max(0.5, min(2.0, 1 + rate / 100))
        samples, sample_rate = model.create(text, voice=voice, speed=speed, lang=lang)
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
        with wave.open(str(target), "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(sample_rate)
            file.writeframes(pcm.tobytes())

    async def synthesize(self, text: str, voice: str, rate: int = 0, pitch: int = 0) -> Path:
        if not kokoro_available():
            raise TTSError("Kokoro no está instalado (pip install kokoro-onnx).")
        if not self.installed:
            raise TTSError("Las voces Kokoro no están descargadas (página Voces → Voces de IA).")
        target = cache_file("kokoro", voice, rate, text, suffix=".wav")
        if target.exists() and target.stat().st_size > 0:
            return target
        async with self._lock:
            try:
                await asyncio.to_thread(self._render, text, voice, rate, target)
            except Exception as error:
                target.unlink(missing_ok=True)
                raise TTSError(f"Kokoro falló: {error}") from error
        return target

    async def warm_up(self):
        """Carga el modelo en segundo plano para que la primera frase no tarde."""
        if self.installed and kokoro_available():
            await asyncio.to_thread(self._load)

    async def download(self, progress=None):
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            total_done = 0
            for name, url in KOKORO_FILES.items():
                target = self.folder / name
                if target.exists():
                    continue
                partial = target.with_name(target.name + ".part")
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=None, sock_read=60)) as response:
                    if response.status != 200:
                        raise TTSError(f"No se pudo descargar {name} ({response.status})")
                    with partial.open("wb") as file:
                        async for chunk in response.content.iter_chunked(512 * 1024):
                            file.write(chunk)
                            total_done += len(chunk)
                            if progress:
                                await progress(min(99, round(total_done * 100 / (KOKORO_SIZE_MB * 1_000_000))))
                partial.replace(target)
        self._model = None

    def delete(self):
        self._model = None
        for name in KOKORO_FILES:
            (self.folder / name).unlink(missing_ok=True)


# ── ElevenLabs ─────────────────────────────────────────────────────────────

ELEVENLABS_API = "https://api.elevenlabs.io/v1"


class ElevenLabsEngine:
    name = "elevenlabs"
    label = "ElevenLabs IA (online, tu clave)"

    def __init__(self, key_provider, model_provider=lambda: "eleven_flash_v2_5"):
        self.key_provider = key_provider
        self.model_provider = model_provider
        self._session: aiohttp.ClientSession | None = None

    def _headers(self) -> dict:
        key = (self.key_provider() or "").strip()
        if not key:
            raise TTSError("ElevenLabs necesita tu clave API (Ajustes → ElevenLabs).")
        return {"xi-api-key": key, "User-Agent": USER_AGENT}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def list_voices(self) -> list[dict]:
        """Voces de la cuenta del usuario (incluye las clonadas). Vacío si no hay clave."""
        if not (self.key_provider() or "").strip():
            return []
        session = await self._get_session()
        async with session.get(f"{ELEVENLABS_API}/voices", headers=self._headers(),
                               timeout=aiohttp.ClientTimeout(total=20)) as response:
            if response.status != 200:
                raise TTSError(f"ElevenLabs respondió {response.status}: {(await response.text())[:150]}")
            data = await response.json(content_type=None)
        voices = []
        for item in data.get("voices", []):
            labels = item.get("labels") or {}
            voices.append({
                "key": item.get("voice_id", ""),
                "name": item.get("name", "Voz"),
                "gender": {"female": "Female", "male": "Male"}.get(str(labels.get("gender", "")).lower(), ""),
                "category": item.get("category", ""),
            })
        return [voice for voice in voices if voice["key"]]

    async def synthesize(self, text: str, voice: str, rate: int = 0, pitch: int = 0) -> Path:
        model = self.model_provider() or "eleven_flash_v2_5"
        target = cache_file("elevenlabs", voice, model, rate, text)
        if target.exists() and target.stat().st_size > 0:
            return target
        session = await self._get_session()
        body = {"text": text[:1000], "model_id": model}
        if rate:
            body["voice_settings"] = {"speed": max(0.7, min(1.2, 1 + rate / 100))}
        try:
            async with session.post(
                f"{ELEVENLABS_API}/text-to-speech/{voice}?output_format=mp3_44100_128",
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                data = await response.read()
                if response.status == 401:
                    raise TTSError("ElevenLabs rechazó la clave API.")
                if response.status == 402 or b"quota" in data[:300]:
                    raise TTSError("Se acabaron los caracteres de tu plan de ElevenLabs este mes.")
                if response.status != 200 or not data:
                    raise TTSError(f"ElevenLabs respondió {response.status}: {data[:150]!r}")
        except TTSError:
            raise
        except Exception as error:
            raise TTSError(f"ElevenLabs falló: {error}") from error
        target.write_bytes(data)
        return target

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
