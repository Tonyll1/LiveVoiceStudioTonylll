from core.config import config
from core.container import container

from gui.main_window import MainWindow

from services.audio.player import AudioPlayer
from services.plugins.actions.sound_action import SoundAction
from services.plugins.command_repository import CommandRepository
from services.plugins.command_service import CommandService
from services.tiktok.blocked_words import BlockedWordsManager
from services.tiktok.client import TikTokClient
from services.tts.manager import TTSManager
from services.tts.voices import VoiceCatalog


class Application:
    def __init__(self):
        self.container = container
        self.window = None

    def setup(self):
        audio_player = AudioPlayer()

        blocked_words_manager = BlockedWordsManager(
            config=config
        )

        voice_catalog = VoiceCatalog()

        command_repository = CommandRepository()
        sound_action = SoundAction()
        command_service = CommandService(
            repository=command_repository,
            sound_action=sound_action
        )

        tts_manager = TTSManager(
            config=config,
            audio_player=audio_player
        )

        tiktok_client = TikTokClient(
            config=config
        )

        # Registrar servicios antes de crear la GUI
        self.container.register(
            "config",
            config
        )

        self.container.register(
            AudioPlayer,
            audio_player
        )

        self.container.register(
            BlockedWordsManager,
            blocked_words_manager
        )

        self.container.register(
            VoiceCatalog,
            voice_catalog
        )

        self.container.register(
            CommandRepository,
            command_repository
        )

        self.container.register(
            SoundAction,
            sound_action
        )

        self.container.register(
            CommandService,
            command_service
        )

        self.container.register(
            TTSManager,
            tts_manager
        )

        self.container.register(
            TikTokClient,
            tiktok_client
        )

        # Iniciar TTS
        tts_manager.start()

        # Crear ventana al final
        self.window = MainWindow(
            self.container
        )

        return self

    def run(self):
        if self.window is None:
            raise RuntimeError(
                "Debes ejecutar setup() antes de run()."
            )

        self.window.mainloop()