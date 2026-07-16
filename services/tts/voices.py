import asyncio
import random
from dataclasses import dataclass

import edge_tts

from core.logger import logger


@dataclass(slots=True, frozen=True)
class Voice:
    short_name: str
    locale: str
    language: str
    country: str
    gender: str
    display_name: str

    @property
    def label(self) -> str:
        gender_text = {
            "Female": "Femenina",
            "Male": "Masculina",
        }.get(self.gender, self.gender)

        return (
            f"{self.display_name} — "
            f"{self.locale} — "
            f"{gender_text}"
        )


FALLBACK_VOICES = [
    Voice(
        short_name="es-MX-DaliaNeural",
        locale="es-MX",
        language="es",
        country="MX",
        gender="Female",
        display_name="Dalia",
    ),
    Voice(
        short_name="es-MX-JorgeNeural",
        locale="es-MX",
        language="es",
        country="MX",
        gender="Male",
        display_name="Jorge",
    ),
    Voice(
        short_name="es-ES-ElviraNeural",
        locale="es-ES",
        language="es",
        country="ES",
        gender="Female",
        display_name="Elvira",
    ),
    Voice(
        short_name="es-ES-AlvaroNeural",
        locale="es-ES",
        language="es",
        country="ES",
        gender="Male",
        display_name="Álvaro",
    ),
]


class VoiceCatalog:
    def __init__(self):
        self._voices: list[Voice] = FALLBACK_VOICES.copy()
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    def get_all(self) -> list[Voice]:
        return list(self._voices)

    def load(self, force: bool = False) -> list[Voice]:
        if self._loaded and not force:
            return self.get_all()

        try:
            voices_data = asyncio.run(
                self._download_voices()
            )

            parsed_voices: list[Voice] = []

            for item in voices_data:
                short_name = str(
                    item.get("ShortName", "")
                ).strip()

                locale = str(
                    item.get("Locale", "")
                ).strip()

                gender = str(
                    item.get("Gender", "")
                ).strip()

                friendly_name = str(
                    item.get("FriendlyName", "")
                ).strip()

                if not short_name or not locale:
                    continue

                language, _, country = locale.partition("-")

                parsed_voices.append(
                    Voice(
                        short_name=short_name,
                        locale=locale,
                        language=language,
                        country=country,
                        gender=gender,
                        display_name=self._extract_display_name(
                            short_name=short_name,
                            friendly_name=friendly_name,
                        ),
                    )
                )

            if parsed_voices:
                parsed_voices.sort(
                    key=lambda voice: (
                        voice.language,
                        voice.country,
                        voice.gender,
                        voice.display_name,
                    )
                )

                self._voices = parsed_voices
                self._loaded = True

        except Exception as error:
            logger.exception(
                "No se pudo cargar el catálogo de voces: %s",
                error,
            )

            self._voices = FALLBACK_VOICES.copy()
            self._loaded = False

        return self.get_all()

    async def _download_voices(self) -> list[dict]:
        return await edge_tts.list_voices()

    def filter(
        self,
        language: str | None = None,
        locale: str | None = None,
        gender: str | None = None,
        search: str | None = None,
    ) -> list[Voice]:
        voices = self.get_all()

        if language and language != "Todos":
            voices = [
                voice
                for voice in voices
                if voice.language.lower() == language.lower()
            ]

        if locale and locale != "Todos":
            voices = [
                voice
                for voice in voices
                if voice.locale.lower() == locale.lower()
            ]

        if gender and gender != "Todos":
            voices = [
                voice
                for voice in voices
                if voice.gender.lower() == gender.lower()
            ]

        if search:
            normalized_search = search.strip().lower()

            voices = [
                voice
                for voice in voices
                if normalized_search in voice.label.lower()
                or normalized_search in voice.short_name.lower()
            ]

        return voices


    def choose_random(
        self,
        language: str | None = None,
        locale: str | None = None,
        gender: str | None = None,
        exclude_voice_id: str | None = None,
    ) -> Voice | None:
        candidates = self.filter(
            language=language,
            locale=locale,
            gender=gender,
        )

        if exclude_voice_id and len(candidates) > 1:
            candidates = [
                voice
                for voice in candidates
                if voice.short_name != exclude_voice_id
            ]

        if not candidates:
            return None

        return random.choice(candidates)

    def get_languages(self) -> list[str]:
        languages = sorted(
            {
                voice.language
                for voice in self._voices
                if voice.language
            }
        )

        return ["Todos", *languages]

    def get_locales(
        self,
        language: str | None = None,
    ) -> list[str]:
        voices = self._voices

        if language and language != "Todos":
            voices = [
                voice
                for voice in voices
                if voice.language == language
            ]

        locales = sorted(
            {
                voice.locale
                for voice in voices
                if voice.locale
            }
        )

        return ["Todos", *locales]

    def get_by_label(
        self,
        label: str,
    ) -> Voice | None:
        for voice in self._voices:
            if voice.label == label:
                return voice

        return None

    def get_by_id(
        self,
        voice_id: str,
    ) -> Voice | None:
        for voice in self._voices:
            if voice.short_name == voice_id:
                return voice

        return None

    @staticmethod
    def _extract_display_name(
        short_name: str,
        friendly_name: str,
    ) -> str:
        if friendly_name and "," in friendly_name:
            possible_name = (
                friendly_name
                .rsplit(",", maxsplit=1)[-1]
                .replace(")", "")
                .strip()
            )

            if possible_name:
                return possible_name.replace(
                    "Neural",
                    "",
                )

        name = short_name.rsplit("-", maxsplit=1)[-1]

        return name.replace(
            "Neural",
            "",
        )