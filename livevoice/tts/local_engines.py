"""Motores de voz extra.

- SapiEngine: voces de Windows (modernas OneCore, SAPI 64 bits y SAPI 32 bits, donde aparecen Loquendo
  y otras voces antiguas instaladas). Sin internet.
- PiperEngine: voces neuronales que corren 100% en tu PC. Se descargan una vez o puedes poner las tuyas.
- TikTokEngine: voces de la app de TikTok (Ghostface, Stormtrooper…). Requiere tu sessionid.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import urllib.parse
import wave
from pathlib import Path

import aiohttp

from livevoice.core.paths import data_path
from livevoice.tts.engines import USER_AGENT, TTSError, cache_file


# ── Windows ────────────────────────────────────────────────────────────────

SYSWOW_POWERSHELL = r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"

SAPI_SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
if ($env:LVS_VOICE) { try { $s.SelectVoice($env:LVS_VOICE) } catch {} }
$s.Rate = [int]$env:LVS_RATE
$s.SetOutputToWaveFile($env:LVS_OUT)
$s.Speak([IO.File]::ReadAllText($env:LVS_TEXT, [Text.Encoding]::UTF8))
$s.Dispose()
"""

SAPI_LIST = r"""
Add-Type -AssemblyName System.Speech
(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | ForEach-Object {
  $v = $_.VoiceInfo; "$($v.Name)|$($v.Culture.Name)|$($v.Gender)" }
"""

WINRT_PRELUDE = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
"""

WINRT_LIST = WINRT_PRELUDE + r"""
[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | ForEach-Object { "$($_.DisplayName)|$($_.Language)|$($_.Gender)" }
"""

WINRT_SCRIPT = WINRT_PRELUDE + r"""
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $type) { $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
$s = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.DisplayName -eq $env:LVS_VOICE } | Select-Object -First 1
if ($voice) { $s.Voice = $voice }
$s.Options.SpeakingRate = [double]$env:LVS_RATE
$s.Options.AudioPitch = [double]$env:LVS_PITCH
$text = [IO.File]::ReadAllText($env:LVS_TEXT, [Text.Encoding]::UTF8)
$stream = Await ($s.SynthesizeTextToStreamAsync($text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
$null = Await ($reader.LoadAsync([uint32]$stream.Size)) ([uint32])
$bytes = New-Object byte[] ($stream.Size)
$reader.ReadBytes($bytes)
[IO.File]::WriteAllBytes($env:LVS_OUT, $bytes)
"""


def run_powershell(script: str, env: dict | None = None, timeout: int = 30, x86: bool = False) -> str:
    if sys.platform != "win32":
        raise TTSError("Las voces de Windows solo están disponibles en Windows.")
    executable = SYSWOW_POWERSHELL if x86 and Path(SYSWOW_POWERSHELL).exists() else "powershell"
    result = subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise TTSError(result.stderr.strip()[:300] or "PowerShell falló")
    return result.stdout


def _parse_voice_lines(output: str) -> list[dict]:
    voices = []
    for line in output.splitlines():
        parts = line.strip().split("|")
        if len(parts) == 3 and parts[0]:
            voices.append({"name": parts[0], "locale": parts[1], "gender": parts[2]})
    return voices


class SapiEngine:
    """Prefijos: win: (OneCore), sapi: (SAPI 64 bits), sapi32: (SAPI 32 bits, p. ej. Loquendo)."""

    name = "sapi"
    label = "Windows (sin internet)"

    async def synthesize(self, text: str, voice: str = "", rate: int = 0, pitch: int = 0, kind: str = "sapi") -> Path:
        target = cache_file(kind, voice, rate, pitch, text, suffix=".wav")
        if target.exists() and target.stat().st_size > 0:
            return target
        text_file = target.with_suffix(".txt")
        text_file.write_text(text, encoding="utf-8")
        env = {"LVS_VOICE": voice, "LVS_OUT": str(target), "LVS_TEXT": str(text_file)}
        try:
            if kind == "win":
                env["LVS_RATE"] = str(max(0.5, min(3.0, 1 + rate / 100)))
                env["LVS_PITCH"] = str(max(0.0, min(2.0, 1 + pitch / 50)))
                await asyncio.to_thread(run_powershell, WINRT_SCRIPT, env)
            else:
                env["LVS_RATE"] = str(max(-10, min(10, round(rate / 10))))
                await asyncio.to_thread(run_powershell, SAPI_SCRIPT, env, 30, kind == "sapi32")
        except subprocess.TimeoutExpired as error:
            raise TTSError("Windows TTS tardó demasiado.") from error
        finally:
            text_file.unlink(missing_ok=True)
        if not target.exists() or target.stat().st_size == 0:
            raise TTSError("Windows TTS no generó audio.")
        return target

    def list_voices(self) -> list[dict]:
        """Todas las voces de Windows sin duplicados; cada una indica con qué sistema se usa."""
        found: dict[str, dict] = {}
        for kind, script, x86 in (("win", WINRT_LIST, False), ("sapi", SAPI_LIST, False), ("sapi32", SAPI_LIST, True)):
            try:
                voices = _parse_voice_lines(run_powershell(script, timeout=20, x86=x86))
            except Exception:
                continue
            for voice in voices:
                short = voice["name"].replace("Microsoft ", "").replace(" Desktop", "").replace(" Mobile", "").lower()
                found.setdefault(short, {**voice, "kind": kind})
        return list(found.values())


# ── TikTok ─────────────────────────────────────────────────────────────────

TIKTOK_VOICES = [
    ("es_mx_002", "Señor mexicano", "es-MX", "Male"), ("es_002", "Español", "es-ES", "Male"),
    ("es_male_m3", "Narrador ES", "es-ES", "Male"), ("es_female_f6", "Alejandra", "es-ES", "Female"),
    ("es_female_fp1", "Mariana", "es-ES", "Female"), ("es_mx_female_supermom", "Super Mamá", "es-MX", "Female"),
    ("es_mx_male_transformer", "Optimus Prime (ES)", "es-MX", "Male"),
    ("en_us_ghostface", "Ghostface", "en-US", "Male"), ("en_us_chewbacca", "Chewbacca", "en-US", "Male"),
    ("en_us_c3po", "C-3PO", "en-US", "Male"), ("en_us_stitch", "Stitch", "en-US", "Male"),
    ("en_us_stormtrooper", "Stormtrooper", "en-US", "Male"), ("en_us_rocket", "Rocket", "en-US", "Male"),
    ("en_male_narration", "Story Teller", "en-US", "Male"), ("en_male_funny", "Wacky", "en-US", "Male"),
    ("en_female_emotional", "Peaceful", "en-US", "Female"), ("en_us_001", "Jessie", "en-US", "Female"),
    ("en_us_006", "Joey (TikTok)", "en-US", "Male"), ("en_male_pirate", "Pirata", "en-US", "Male"),
    ("en_female_madam_leota", "Madame Leota", "en-US", "Female"), ("en_male_ghosthost", "Ghost Host", "en-US", "Male"),
    ("en_female_f08_salut_damour", "Cantante (Salut d'amour)", "en-US", "Female"),
    ("en_male_m03_lobby", "Cantante (Lobby)", "en-US", "Male"),
    ("jp_001", "Japonesa", "ja-JP", "Female"), ("kr_002", "Coreano", "ko-KR", "Male"),
    ("br_003", "Brasileña", "pt-BR", "Female"), ("fr_001", "Francés", "fr-FR", "Male"), ("de_001", "Alemana", "de-DE", "Female"),
]


class TikTokEngine:
    name = "tiktok"
    label = "Voces de TikTok (experimental)"
    HOSTS = (
        "api16-normal-c-useast1a.tiktokv.com",
        "api16-normal-c-useast2a.tiktokv.com",
        "api16-normal-useast5.us.tiktokv.com",
    )
    APP_UA = "com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)"

    def __init__(self, session_id_provider):
        self.session_id_provider = session_id_provider
        self._session: aiohttp.ClientSession | None = None

    async def synthesize(self, text: str, voice: str = "es_mx_002", rate: int = 0, pitch: int = 0) -> Path:
        target = cache_file("tiktok", voice, text)
        if target.exists() and target.stat().st_size > 0:
            return target
        session_id = (self.session_id_provider() or "").strip()
        if not session_id:
            raise TTSError("Las voces de TikTok necesitan tu sessionid (Ajustes → Voces de TikTok).")
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers={"User-Agent": self.APP_UA})
        query = urllib.parse.urlencode({"text_speaker": voice, "req_text": text[:300], "speaker_map_type": 0, "aid": 1233})
        last_error = "sin respuesta"
        for host in self.HOSTS:
            try:
                async with self._session.post(
                    f"https://{host}/media/api/text/speech/invoke/?{query}",
                    headers={"Cookie": f"sessionid={session_id}", "Content-Length": "0"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    data = await response.json(content_type=None)
                audio = (data.get("data") or {}).get("v_str")
                if data.get("status_code") == 0 and audio:
                    target.write_bytes(base64.b64decode(audio))
                    return target
                last_error = data.get("status_msg") or data.get("message") or str(data.get("status_code"))
            except Exception as error:
                last_error = str(error)
        raise TTSError(f"TikTok TTS falló: {last_error}")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ── Piper ──────────────────────────────────────────────────────────────────

PIPER_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
PIPER_LANGUAGES = ("es_", "en_US", "en_GB", "pt_BR", "fr_FR", "it_IT", "de_DE")


def piper_available() -> bool:
    try:
        import piper  # noqa: F401
    except Exception as error:
        from livevoice.core.logger import logger

        logger.warning("Piper no se pudo cargar: %r", error)
        return False
    return True


class PiperEngine:
    name = "piper"
    label = "Piper (neuronal, sin internet)"

    def __init__(self):
        self.folder = data_path("voices", "piper", "x").parent
        self._loaded: dict[str, object] = {}
        self._lock = asyncio.Lock()

    def model_path(self, key: str) -> Path:
        return self.folder / f"{key}.onnx"

    def installed(self) -> list[dict]:
        """Modelos .onnx presentes en voices/piper (descargados o entrenados por ti)."""
        voices = []
        for model in sorted(self.folder.glob("*.onnx")):
            config = model.with_suffix(".onnx.json")
            if not config.exists():
                continue
            locale = model.stem.split("-")[0]
            try:
                info = json.loads(config.read_text(encoding="utf-8"))
                locale = (info.get("language") or {}).get("code", locale)
            except Exception:
                pass
            voices.append({"key": model.stem, "locale": locale.replace("_", "-")})
        return voices

    def _load(self, key: str):
        from piper import PiperVoice

        if key not in self._loaded:
            if len(self._loaded) >= 3:
                self._loaded.pop(next(iter(self._loaded)))
            self._loaded[key] = PiperVoice.load(str(self.model_path(key)))
        return self._loaded[key]

    def _render(self, key: str, text: str, rate: int, target: Path):
        from piper import SynthesisConfig

        voice = self._load(key)
        length_scale = max(0.4, min(2.0, 1 / max(0.3, 1 + rate / 100)))
        with wave.open(str(target), "wb") as file:
            voice.synthesize_wav(text, file, syn_config=SynthesisConfig(length_scale=length_scale))

    async def synthesize(self, text: str, voice: str, rate: int = 0, pitch: int = 0) -> Path:
        if not piper_available():
            raise TTSError("Piper no está instalado (pip install piper-tts).")
        if not self.model_path(voice).exists():
            raise TTSError(f"La voz Piper {voice} no está descargada.")
        target = cache_file("piper", voice, rate, text, suffix=".wav")
        if target.exists() and target.stat().st_size > 0:
            return target
        async with self._lock:
            try:
                await asyncio.to_thread(self._render, voice, text, rate, target)
            except Exception as error:
                target.unlink(missing_ok=True)
                raise TTSError(f"Piper falló: {error}") from error
        return target

    async def fetch_catalog(self) -> list[dict]:
        """Voces Piper descargables (idiomas útiles) desde el repositorio oficial de Piper."""
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            async with session.get(PIPER_BASE_URL + "voices.json", timeout=aiohttp.ClientTimeout(total=30)) as response:
                data = await response.json(content_type=None)
        catalog = []
        for key, info in data.items():
            if not key.startswith(PIPER_LANGUAGES):
                continue
            files = info.get("files", {})
            onnx = next((path for path in files if path.endswith(".onnx")), None)
            if not onnx:
                continue
            language = info.get("language", {})
            catalog.append({
                "key": key,
                "name": info.get("name", key),
                "quality": info.get("quality", ""),
                "locale": language.get("code", "").replace("_", "-"),
                "country": language.get("country_english", ""),
                "size_mb": round(files[onnx].get("size_bytes", 0) / 1_000_000),
                "path": onnx,
                "speakers": info.get("num_speakers", 1),
            })
        catalog.sort(key=lambda item: (not item["key"].startswith("es_"), item["key"]))
        return catalog

    async def download(self, entry: dict, progress=None):
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            for suffix in (".onnx.json", ".onnx"):
                url = PIPER_BASE_URL + entry["path"].removesuffix(".onnx") + suffix
                target = self.folder / f"{entry['key']}{suffix}"
                partial = target.with_name(target.name + ".part")
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=None, sock_read=60)) as response:
                    if response.status != 200:
                        raise TTSError(f"No se pudo descargar {entry['key']} ({response.status})")
                    total = int(response.headers.get("Content-Length", 0))
                    done = 0
                    with partial.open("wb") as file:
                        async for chunk in response.content.iter_chunked(256 * 1024):
                            file.write(chunk)
                            done += len(chunk)
                            if progress and suffix == ".onnx" and total:
                                await progress(round(done * 100 / total))
                partial.replace(target)

    def delete(self, key: str):
        self._loaded.pop(key, None)
        for suffix in (".onnx", ".onnx.json"):
            (self.folder / f"{key}{suffix}").unlink(missing_ok=True)
