"""Catálogo de voces: Edge (+300), Windows y Google, más personajes y alias para el chat."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass

from livevoice.core.logger import logger
from livevoice.core.paths import data_path
from livevoice.tts.engines import EdgeEngine, SapiEngine


LANGUAGE_NAMES = {
    "es": "Español", "en": "Inglés", "pt": "Portugués", "fr": "Francés", "it": "Italiano",
    "de": "Alemán", "ja": "Japonés", "ko": "Coreano", "zh": "Chino", "ru": "Ruso",
    "ar": "Árabe", "hi": "Hindi", "tr": "Turco", "nl": "Neerlandés", "pl": "Polaco",
    "ca": "Catalán", "gl": "Gallego", "eu": "Euskera", "uk": "Ucraniano", "sv": "Sueco",
}

COUNTRY_NAMES = {
    "MX": "México", "ES": "España", "AR": "Argentina", "CO": "Colombia", "CL": "Chile",
    "PE": "Perú", "VE": "Venezuela", "US": "Estados Unidos", "GB": "Reino Unido", "CU": "Cuba",
    "DO": "Rep. Dominicana", "EC": "Ecuador", "GT": "Guatemala", "HN": "Honduras", "NI": "Nicaragua",
    "PA": "Panamá", "PY": "Paraguay", "PR": "Puerto Rico", "SV": "El Salvador", "UY": "Uruguay",
    "BO": "Bolivia", "CR": "Costa Rica", "GQ": "Guinea Ecuatorial", "BR": "Brasil", "PT": "Portugal",
    "FR": "Francia", "IT": "Italia", "DE": "Alemania", "JP": "Japón", "KR": "Corea", "CN": "China",
    "RU": "Rusia", "AU": "Australia", "CA": "Canadá", "IN": "India", "IE": "Irlanda",
}

# Personajes: modifican tono y velocidad sobre cualquier voz.
PRESETS = [
    {"id": "normal", "name": "Normal", "emoji": "🙂", "pitch": 0, "rate": 0},
    {"id": "ardilla", "name": "Ardilla", "emoji": "🐿️", "pitch": 50, "rate": 25},
    {"id": "nino", "name": "Niño", "emoji": "🧒", "pitch": 30, "rate": 10},
    {"id": "gigante", "name": "Gigante", "emoji": "👹", "pitch": -45, "rate": -15},
    {"id": "abuelo", "name": "Abuelo", "emoji": "👴", "pitch": -20, "rate": -25},
    {"id": "rapido", "name": "Rapidito", "emoji": "⚡", "pitch": 0, "rate": 60},
    {"id": "lento", "name": "Lento", "emoji": "🐢", "pitch": -5, "rate": -40},
    {"id": "narrador", "name": "Narrador", "emoji": "🎙️", "pitch": -12, "rate": -8},
    {"id": "robot", "name": "Robot", "emoji": "🤖", "pitch": -30, "rate": 15},
    {"id": "chipmunk", "name": "Helio", "emoji": "🎈", "pitch": 50, "rate": 50},
]
PRESETS_BY_ID = {preset["id"]: preset for preset in PRESETS}

# Alias que los espectadores pueden usar con !voz <alias>
VOICE_ALIASES = {
    "mexicano": "es-MX-JorgeNeural", "mx": "es-MX-JorgeNeural", "mexicana": "es-MX-DaliaNeural",
    "espanol": "es-ES-AlvaroNeural", "espana": "es-ES-AlvaroNeural", "espanola": "es-ES-ElviraNeural",
    "argentino": "es-AR-TomasNeural", "argentina": "es-AR-ElenaNeural",
    "colombiano": "es-CO-GonzaloNeural", "colombiana": "es-CO-SalomeNeural",
    "chileno": "es-CL-LorenzoNeural", "chilena": "es-CL-CatalinaNeural",
    "peruano": "es-PE-AlexNeural", "peruana": "es-PE-CamilaNeural",
    "venezolano": "es-VE-SebastianNeural", "venezolana": "es-VE-PaolaNeural",
    "cubano": "es-CU-ManuelNeural", "cubana": "es-CU-BelkysNeural",
    "dominicano": "es-DO-EmilioNeural", "dominicana": "es-DO-RamonaNeural",
    "gringo": "en-US-GuyNeural", "gringa": "en-US-JennyNeural",
    "ingles": "en-GB-RyanNeural", "inglesa": "en-GB-SoniaNeural",
    "brasileno": "pt-BR-AntonioNeural", "brasilena": "pt-BR-FranciscaNeural",
    "frances": "fr-FR-HenriNeural", "francesa": "fr-FR-DeniseNeural",
    "italiano": "it-IT-DiegoNeural", "italiana": "it-IT-ElsaNeural",
    "aleman": "de-DE-ConradNeural", "alemana": "de-DE-KatjaNeural",
    "japones": "ja-JP-KeitaNeural", "japonesa": "ja-JP-NanamiNeural",
    "ruso": "ru-RU-DmitryNeural", "rusa": "ru-RU-SvetlanaNeural",
    "coreano": "ko-KR-InJoonNeural", "coreana": "ko-KR-SunHiNeural",
}

FALLBACK_EDGE = [
    ("es-MX-DaliaNeural", "Female"), ("es-MX-JorgeNeural", "Male"),
    ("es-ES-ElviraNeural", "Female"), ("es-ES-AlvaroNeural", "Male"),
    ("es-AR-ElenaNeural", "Female"), ("es-AR-TomasNeural", "Male"),
    ("es-CO-SalomeNeural", "Female"), ("es-CO-GonzaloNeural", "Male"),
    ("en-US-JennyNeural", "Female"), ("en-US-GuyNeural", "Male"),
]


@dataclass(slots=True)
class Voice:
    id: str
    engine: str
    name: str
    locale: str
    gender: str

    @property
    def language(self) -> str:
        return self.locale.split("-")[0].lower()

    def to_dict(self) -> dict:
        data = asdict(self)
        country = self.locale.split("-")[1] if "-" in self.locale else ""
        data["language"] = self.language
        data["language_name"] = LANGUAGE_NAMES.get(self.language, self.language)
        data["country"] = COUNTRY_NAMES.get(country, country)
        return data


def engine_for(voice_id: str) -> str:
    if voice_id.startswith("sapi:"):
        return "sapi"
    if voice_id.startswith("google:"):
        return "google"
    return "edge"


def _edge_name(short_name: str) -> str:
    return short_name.rsplit("-", 1)[-1].replace("Neural", "").replace("Multilingual", " Multi")


def normalize_alias(text: str) -> str:
    replacements = str.maketrans("áéíóúñü", "aeiounu")
    return text.strip().lower().translate(replacements)


class VoiceCatalog:
    def __init__(self):
        self.cache_file = data_path("data", "voices.json")
        self.voices: list[Voice] = []
        self._by_id: dict[str, Voice] = {}
        self._load_cached()

    def _set(self, voices: list[Voice]):
        voices.sort(key=lambda voice: (voice.engine != "edge", voice.language != "es", voice.locale, voice.name))
        self.voices = voices
        self._by_id = {voice.id: voice for voice in voices}

    def _google_voices(self) -> list[Voice]:
        return [
            Voice(id=f"google:{code}", engine="google", name=f"Google {name}", locale=code, gender="Neutral")
            for code, name in LANGUAGE_NAMES.items()
        ]

    def _load_cached(self):
        voices: list[Voice] = []
        if self.cache_file.exists():
            try:
                voices = [Voice(**item) for item in json.loads(self.cache_file.read_text(encoding="utf-8"))]
            except Exception:
                voices = []
        if not voices:
            voices = [
                Voice(id=short, engine="edge", name=_edge_name(short), locale="-".join(short.split("-")[:2]), gender=gender)
                for short, gender in FALLBACK_EDGE
            ] + self._google_voices()
        self._set(voices)

    async def refresh(self):
        """Descarga la lista actual de Edge y detecta las voces de Windows. Se guarda en disco."""
        voices: list[Voice] = []
        try:
            for item in await EdgeEngine.list_voices():
                short = item.get("ShortName", "")
                if not short:
                    continue
                voices.append(Voice(
                    id=short,
                    engine="edge",
                    name=_edge_name(short),
                    locale=item.get("Locale", ""),
                    gender=item.get("Gender", ""),
                ))
        except Exception as error:
            logger.warning("No se pudo descargar el catálogo de Edge: %s", error)
            voices = [voice for voice in self.voices if voice.engine == "edge"]

        try:
            for item in await asyncio.to_thread(SapiEngine().list_voices):
                voices.append(Voice(
                    id=f"sapi:{item['name']}",
                    engine="sapi",
                    name=item["name"].replace("Microsoft ", "").replace(" Desktop", ""),
                    locale=item["locale"],
                    gender=item["gender"],
                ))
        except Exception as error:
            logger.warning("No se pudieron listar las voces de Windows: %s", error)

        voices += self._google_voices()
        self._set(voices)
        try:
            self.cache_file.write_text(json.dumps([asdict(voice) for voice in voices], ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        return self.voices

    def get(self, voice_id: str) -> Voice | None:
        return self._by_id.get(voice_id)

    def by_language(self, language: str, engine: str = "edge") -> list[Voice]:
        return [voice for voice in self.voices if voice.language == language and voice.engine == engine]

    def random_for(self, user_key: str, language: str) -> str | None:
        """Voz estable por usuario: el mismo espectador siempre suena igual."""
        pool = self.by_language(language) or self.by_language("es")
        if not pool:
            return None
        index = int(hashlib.md5(user_key.encode("utf-8")).hexdigest(), 16) % len(pool)
        return pool[index].id

    def resolve_alias(self, alias: str) -> tuple[str | None, str | None]:
        """Traduce lo que escribe el espectador en (voice_id, preset_id)."""
        alias = normalize_alias(alias)
        if alias in PRESETS_BY_ID:
            return None, alias
        for preset in PRESETS:
            if normalize_alias(preset["name"]) == alias:
                return None, preset["id"]
        if alias in VOICE_ALIASES:
            return VOICE_ALIASES[alias], None
        return None, None

    def to_list(self) -> list[dict]:
        return [voice.to_dict() for voice in self.voices]
