import threading

from core.constants import (
    COMMENT_EVENT,
    FOLLOW_EVENT,
    GIFT_EVENT,
    TTS_SPEAK_EVENT
)
from core.event_bus import event_bus
from core.events import Priority
from core.logger import logger

from models.comment import Comment
from models.follow import Follow
from models.gift import Gift

from services.audio.cache import AudioCache
from services.audio.player import AudioPlayer
from services.tts.edge_engine import EdgeEngine
from services.tts.formatter import Formatter
from services.tts.queue import TTSQueue
from services.tts.voices import VoiceCatalog


class TTSManager:
    def __init__(
        self,
        config,
        audio_player: AudioPlayer,
        voice_catalog: VoiceCatalog
    ):
        self.config = config
        self.audio_player = audio_player
        self.voice_catalog = voice_catalog
        self._last_random_voice = None

        self.cache = AudioCache()
        self.queue = TTSQueue()

        self.engine = EdgeEngine(
            cache=self.cache
        )

        self.running = False
        self.thread = None

        event_bus.subscribe(
            COMMENT_EVENT,
            self.on_comment,
            priority=Priority.NORMAL
        )

        event_bus.subscribe(
            FOLLOW_EVENT,
            self.on_follow,
            priority=Priority.HIGH
        )

        event_bus.subscribe(
            GIFT_EVENT,
            self.on_gift,
            priority=Priority.CRITICAL
        )

        event_bus.subscribe(
            TTS_SPEAK_EVENT,
            self.speak,
            priority=Priority.NORMAL
        )

    def start(self):
        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self.worker,
            daemon=True
        )

        self.thread.start()

    def stop(self):
        self.running = False
        self.audio_player.stop()

    def worker(self):
        while self.running:
            text, _priority = self.queue.next()

            try:
                voice = self._get_voice_for_next_message()

                rate = self.config.get(
                    "rate",
                    "+0%"
                )

                volume = self.config.get(
                    "volume",
                    "+0%"
                )

                filename = self.engine.synthesize(
                    text=text,
                    voice=voice,
                    rate=rate,
                    volume=volume
                )

                self.audio_player.play(filename)

            except Exception as error:
                logger.exception(
                    "Error en TTS: %s",
                    error
                )

    def _get_voice_for_next_message(self) -> str:
        configured_voice = self.config.get(
            "voice",
            "es-MX-DaliaNeural"
        )

        if not self.config.get("random_voice", False):
            return configured_voice

        selected = self.voice_catalog.choose_random(
            language=self.config.get("random_voice_language", "es"),
            locale=self.config.get("random_voice_locale", "Todos"),
            gender=self.config.get("random_voice_gender", "Todos"),
            exclude_voice_id=self._last_random_voice,
        )

        if selected is None:
            return configured_voice

        self._last_random_voice = selected.short_name
        return selected.short_name

    def speak(
        self,
        text: str,
        priority: Priority | int = Priority.NORMAL
    ):
        if not text:
            return

        text = text.strip()

        if not text:
            return

        self.queue.add(
            text=text,
            priority=priority
        )

    def set_voice(self, voice_id: str):
        self.config.set(
            "voice",
            voice_id
        )

    def test_voice(self):
        self.speak(
            "Hola Marco. Esta es una prueba de voz de LiveVoice Studio.",
            priority=Priority.CRITICAL
        )

    def on_comment(
        self,
        comment: Comment,
        read_tts: bool = True
    ):
        if not read_tts:
            return

        if comment.text.strip().startswith("!"):
            return

        if not self.config.get("read_comments", True):
            return

        text = Formatter.comment(
            comment,
            include_username=self.config.get(
                "read_username",
                True
            )
        )

        self.speak(
            text,
            priority=Priority.NORMAL
        )

    def on_follow(self, follow: Follow):
        if not self.config.get("read_followers", True):
            return

        text = Formatter.follow(follow)

        self.speak(
            text,
            priority=Priority.HIGH
        )

    def on_gift(self, gift: Gift):
        if not self.config.get("read_gifts", True):
            return

        text = Formatter.gift(gift)

        self.speak(
            text,
            priority=Priority.CRITICAL
        )