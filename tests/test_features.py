import asyncio

import pytest

from livevoice.app import Studio
from livevoice.core.config import Config
from livevoice.core.models import LiveEvent, User


class FakePlayer:
    available = True
    device = ""

    def __init__(self):
        self.effects = []

    def play_effect(self, path, volume=None):
        self.effects.append(path)

    def stop_voice(self):
        pass

    def set_volumes(self, *args):
        pass


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setattr("livevoice.app.AudioPlayer", lambda *args, **kwargs: FakePlayer())
    monkeypatch.setattr("livevoice.core.stats.data_path", lambda *parts: tmp_path.joinpath(*parts))
    (tmp_path / "data").mkdir()
    return Studio(Config(tmp_path / "config.json"))


def event(kind="chat", text="", name="ana", platform="twitch", **kwargs):
    flags = {key: kwargs.pop(key) for key in list(kwargs) if key.startswith("is_")}
    return LiveEvent(kind=kind, platform=platform, user=User(platform=platform, username=name, display_name=name, **flags), text=text, **kwargs)


def spoken(studio):
    return [item.text for item in studio.tts.pending]


def test_chat_is_read_with_welcome(studio):
    asyncio.run(studio.on_live_event(event(text="hola")))
    texts = spoken(studio)
    assert any("Bienvenido ana" in text for text in texts)
    assert "ana dice: hola" in texts


def test_voice_command_assigns_user_voice(studio):
    asyncio.run(studio.on_live_event(event(text="!voz argentino")))
    assert studio.config.get("tts.user_voices")["twitch:ana"]["voice"] == "es-AR-TomasNeural"
    voice, _, _ = studio.tts.voice_for_user("twitch:ana")
    assert voice == "es-AR-TomasNeural"


def test_custom_sound_command_with_cooldown(studio, tmp_path):
    sound = tmp_path / "susto.mp3"
    sound.write_bytes(b"x")
    studio.config.set("commands", [{"name": "!susto", "sound": str(sound), "text": "", "cooldown": 30, "permission": "everyone"}])
    asyncio.run(studio.on_live_event(event(text="!susto")))
    asyncio.run(studio.on_live_event(event(text="!susto ahora")))
    assert studio.player.effects == [str(sound)]


def test_moderator_only_command(studio, tmp_path):
    sound = tmp_path / "s.wav"
    sound.write_bytes(b"x")
    studio.config.set("commands", [{"name": "!mod", "sound": str(sound), "permission": "moderators"}])
    asyncio.run(studio.on_live_event(event(text="!mod")))
    asyncio.run(studio.on_live_event(event(text="!mod", name="jefe", is_moderator=True)))
    assert len(studio.player.effects) == 1


def test_gift_alert_goal_and_points(studio):
    studio.config.set("goals.gifts.target", 10)
    asyncio.run(studio.on_live_event(event(kind="gift", gift="Rosa", amount=10, value=10, platform="tiktok")))
    texts = spoken(studio)
    assert any("envió 10 Rosa" in text for text in texts)
    assert any("Meta cumplida" in text for text in texts)
    assert studio.viewers.get("tiktok:ana")["points"] == 50
    assert studio.stats.top_gifters()[0]["value"] == 10


def test_poll_and_giveaway(studio):
    async def scenario():
        await studio.giveaway.start("!entro")
        await studio.on_live_event(event(text="!entro", name="a"))
        await studio.on_live_event(event(text="!entro", name="a"))
        await studio.on_live_event(event(text="!entro", name="b", platform="kick"))
        assert studio.giveaway.state()["count"] == 2

        await studio.poll.start("¿Juego?", ["Minecraft", "Fortnite"], 60)
        await studio.on_live_event(event(text="2", name="a"))
        await studio.on_live_event(event(text="1", name="b"))
        await studio.on_live_event(event(text="2", name="c"))
        results = studio.poll.results()
        await studio.poll.finish()
        return results

    results = asyncio.run(scenario())
    assert [item["votes"] for item in results] == [1, 2]


def test_like_milestones(studio):
    studio.config.set("alerts.like.min_amount", 100)
    asyncio.run(studio.on_live_event(event(kind="like", amount=60, platform="tiktok")))
    assert not any("likes" in text for text in spoken(studio))
    asyncio.run(studio.on_live_event(event(kind="like", amount=60, platform="tiktok")))
    assert any("100 likes" in text for text in spoken(studio))
