import asyncio
import json
from pathlib import Path

import pytest

from livevoice.core.config import Config
from livevoice.core.models import LiveEvent, User
from livevoice.features.chat_reader import ChatReader
from livevoice.features.moderation import Moderation
from livevoice.platforms.base import PlatformClient
from livevoice.platforms.twitch import parse_irc
from livevoice.platforms.youtube import YouTubePlatform
from livevoice.tts import manager as manager_module
from livevoice.tts.engines import TTSError
from livevoice.tts.manager import TTSManager
from livevoice.tts.text import clean_for_speech, render
from livevoice.tts.voices import VoiceCatalog


@pytest.fixture
def config(tmp_path):
    return Config(tmp_path / "config.json")


def chat(text, platform="twitch", name="ana", **flags):
    return LiveEvent(kind="chat", platform=platform, user=User(platform=platform, username=name, display_name=name, **flags), text=text)


class FakeTTS:
    def __init__(self):
        self.said = []

    def say(self, text, **kwargs):
        self.said.append(text)


def test_config_defaults_and_dotted_access(config):
    assert config.get("tts.voice") == "es-MX-DaliaNeural"
    config.set("tts.rate", 20)
    assert Config(config.filename).get("tts.rate") == 20


def test_config_migrates_legacy_format(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"username": "itsertm2", "voice": "es-DO-EmilioNeural", "read_gifts": False}), encoding="utf-8")
    config = Config(path)
    assert config.get("platforms.tiktok.channel") == "itsertm2"
    assert config.get("tts.voice") == "es-DO-EmilioNeural"
    assert config.get("tts.read_events.gift") is False


def test_config_update_replaces_lists(config):
    config.update({"commands": [{"name": "!a"}]})
    config.update({"commands": [{"name": "!b"}]})
    assert config.get("commands") == [{"name": "!b"}]


def test_clean_for_speech():
    assert clean_for_speech("holaaaaaa mira https://x.com/a") == "holaa mira un enlace"
    assert clean_for_speech("jajajajaja xd", replacements={"xd": "equis de"}) == "jajaja equis de"
    assert clean_for_speech("hola 😂🔥") == "hola"
    assert clean_for_speech("[emote:37226:KEKW] lol") == "KEKW lol"
    assert len(clean_for_speech("palabra " * 100, max_length=50)) <= 50


def test_render_tolerates_missing_keys():
    assert render("{user} dice: {message}", user="Ana", message="hola") == "Ana dice: hola"
    assert render("{user} {nope}", user="Ana") == "Ana"


def test_moderation_spam_and_blocked_words(config):
    moderation = Moderation(config)
    first = chat("hola a todos")
    assert moderation.check(first) and first.tts_allowed
    repeat = chat("Hola a todos")
    assert moderation.check(repeat) and not repeat.tts_allowed

    config.set("moderation.blocked_words", ["feo"])
    censored = chat("eres feo jaja", name="bob")
    assert moderation.check(censored) and censored.text == "eres *** jaja"
    config.set("moderation.blocked_mode", "hide")
    assert not moderation.check(chat("muy feo", name="carl"))


def test_chat_reader_rules(config):
    tts = FakeTTS()
    reader = ChatReader(config, tts, lambda: set())
    assert reader.read(chat("hola"))
    assert tts.said[-1] == "ana dice: hola"
    assert not reader.read(chat("!comando"))
    assert not reader.read(chat("spam", name="Nightbot"))

    config.set("tts.prefix", "!tts")
    assert not reader.read(chat("sin prefijo"))
    assert reader.read(chat("!tts con prefijo"))
    assert tts.said[-1] == "ana dice: con prefijo"

    config.set("tts.prefix", "")
    config.set("tts.who", "moderators")
    assert not reader.read(chat("hola", name="x"))
    assert reader.read(chat("hola", name="mod", is_moderator=True))


def test_twitch_irc_parser():
    line = "@badges=moderator/1;display-name=Ana\\sB;mod=1 :ana!ana@ana.tmi.twitch.tv PRIVMSG #canal :hola mundo"
    msg = parse_irc(line)
    assert msg["command"] == "PRIVMSG"
    assert msg["tags"]["display-name"] == "Ana B"
    assert msg["text"] == "hola mundo"


def test_channel_normalization():
    assert PlatformClient.normalize_channel("https://www.tiktok.com/@usuario/live") == "usuario"
    assert PlatformClient.normalize_channel("@usuario") == "usuario"
    assert YouTubePlatform.normalize_channel("https://www.youtube.com/watch?v=0sfDth4lMLc") == "0sfDth4lMLc"
    assert YouTubePlatform.normalize_channel("https://youtube.com/@LofiGirl/live") == "@LofiGirl"


def test_voice_aliases():
    catalog = VoiceCatalog()
    assert catalog.resolve_alias("Argentino") == ("es-AR-TomasNeural", None)
    assert catalog.resolve_alias("ardilla") == (None, "ardilla")
    assert catalog.resolve_alias("japonés") == ("ja-JP-KeitaNeural", None)
    assert catalog.resolve_alias("xyz") == (None, None)
    assert catalog.random_for("twitch:ana", "es") == catalog.random_for("twitch:ana", "es")


class _Player:
    def stop_voice(self):
        pass


def test_tts_falls_back_when_edge_fails(config, tmp_path):
    async def scenario():
        manager = TTSManager(config, _Player(), VoiceCatalog())

        async def broken(*args, **kwargs):
            raise TTSError("403 Forbidden")

        async def google(text, lang="es", *args):
            return tmp_path / f"google-{lang}.mp3"

        manager.engines["edge"].synthesize = broken
        manager.engines["google"].synthesize = google
        item = manager.say("hola")
        path = await manager.synthesize(item)
        assert path.name == "google-es.mp3"
        assert manager.engine_status["edge"]["ok"] is False
        assert manager.engine_status["google"]["ok"] is True

    asyncio.run(scenario())


def test_tts_queue_trims_chat_but_keeps_alerts(config):
    async def scenario():
        config.set("tts.max_queue", 3)
        manager = TTSManager(config, _Player(), VoiceCatalog())
        manager.say("alerta", priority=manager_module.PRIORITY_ALERT)
        for index in range(5):
            manager.say(f"chat {index}")
        texts = [item.text for item in manager.pending]
        assert texts[0] == "alerta"
        assert len(texts) == 3 and "chat 4" in texts

        manager.set_muted(True)
        assert manager.say("silenciado") is None

    asyncio.run(scenario())
