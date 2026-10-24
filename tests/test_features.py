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
    monkeypatch.setattr("livevoice.features.gift_catalog.data_path", lambda *parts: tmp_path.joinpath(*parts))
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


def welcomes(studio):
    return [text for text in spoken(studio) if text.startswith(("Bienvenido", "Qué bueno"))]


def test_welcome_only_new_viewers_by_default(studio):
    studio.config.set("welcome.cooldown", 0)
    asyncio.run(studio.on_live_event(event(text="hola", name="tatiana")))
    assert welcomes(studio) == ["Bienvenido tatiana, gracias por pasar."]

    # Nueva sesión: tatiana ya escribió antes en el canal, no se la vuelve a saludar.
    studio.stats.reset()
    studio.tts.pending.clear()
    asyncio.run(studio.on_live_event(event(text="otra vez yo", name="tatiana")))
    assert welcomes(studio) == []


def test_welcome_session_mode_greets_returning_viewers(studio):
    studio.config.update({"welcome": {"mode": "session", "cooldown": 0, "text_back": "Qué bueno verte, {user}"}})
    asyncio.run(studio.on_live_event(event(text="hola", name="tatiana")))
    studio.stats.reset()
    studio.tts.pending.clear()
    asyncio.run(studio.on_live_event(event(text="volví", name="tatiana")))
    assert welcomes(studio) == ["Qué bueno verte, tatiana"]


def test_welcome_cooldown_and_busy_queue(studio):
    studio.config.update({"welcome": {"cooldown": 60, "max_queue": 99}})
    asyncio.run(studio.on_live_event(event(text="hola", name="a")))
    asyncio.run(studio.on_live_event(event(text="hola", name="b")))
    assert len(welcomes(studio)) == 1

    studio.config.update({"welcome": {"cooldown": 0, "max_queue": 1}})
    asyncio.run(studio.on_live_event(event(text="hola", name="c")))
    assert len(welcomes(studio)) == 1


def test_welcome_can_be_disabled(studio):
    studio.config.set("welcome.enabled", False)
    asyncio.run(studio.on_live_event(event(text="hola", name="tatiana")))
    assert welcomes(studio) == []
    assert "tatiana dice: hola" in spoken(studio)


def test_custom_alert_replaces_default_for_matching_gift(studio, tmp_path):
    sound = tmp_path / "boom.mp3"
    sound.write_bytes(b"x")
    studio.config.set("custom_alerts", [{
        "id": "1", "name": "Galaxia", "trigger": "gift", "match": "galaxia", "min_amount": 0,
        "sound": str(sound), "tts_text": "¡{user} lanzó una galaxia!", "voice": "es-MX-JorgeNeural",
        "media": str(tmp_path / "boom.gif"), "replace_default": True,
    }])
    published = []
    studio_bus = __import__("livevoice.core.bus", fromlist=["bus"]).bus
    studio_bus.on("ws", lambda kind, data: published.append((kind, data)))
    asyncio.run(studio.on_live_event(event(kind="gift", gift="Galaxia", amount=1, value=1000, platform="tiktok")))
    asyncio.run(studio.on_live_event(event(kind="gift", gift="Rosa", amount=1, value=1, platform="tiktok", name="bob")))

    texts = spoken(studio)
    assert "¡ana lanzó una galaxia!" in texts
    assert not any("envió 1 Galaxia" in text for text in texts)  # la alerta normal se reemplazó
    assert any("envió 1 Rosa" in text for text in texts)          # la Rosa sigue con la alerta normal
    assert studio.player.effects == [str(sound)]
    assert next(item for item in studio.tts.pending if "galaxia" in item.text).voice == "es-MX-JorgeNeural"
    alerts = [data for kind, data in published if kind == "alert" and data.get("custom")]
    assert alerts and alerts[0]["media"] == "/media/boom.gif"


def test_custom_alert_chat_keyword_and_cooldown(studio, tmp_path):
    sound = tmp_path / "risa.wav"
    sound.write_bytes(b"x")
    studio.config.set("custom_alerts", [{
        "id": "2", "name": "Risa", "trigger": "chat", "match": "jajaja", "sound": str(sound), "cooldown": 60,
    }])
    asyncio.run(studio.on_live_event(event(text="JAJAJA qué risa", name="a")))
    asyncio.run(studio.on_live_event(event(text="jajaja otra vez", name="b")))
    asyncio.run(studio.on_live_event(event(text="hola", name="c")))
    assert studio.player.effects == [str(sound)]
    assert "a dice: jajaja qué risa" in [item.text for item in studio.tts.pending]  # el mensaje se sigue leyendo


def test_custom_alert_platform_and_minimum(studio):
    studio.config.set("custom_alerts", [{
        "id": "3", "name": "Raid grande", "trigger": "raid", "min_amount": 50, "platforms": ["twitch"],
        "tts_text": "Raid enorme de {user}",
    }])
    asyncio.run(studio.on_live_event(event(kind="raid", amount=10, platform="twitch", name="chico")))
    asyncio.run(studio.on_live_event(event(kind="raid", amount=80, platform="kick", name="kickero")))
    asyncio.run(studio.on_live_event(event(kind="raid", amount=80, platform="twitch", name="grande")))
    texts = spoken(studio)
    assert "Raid enorme de grande" in texts
    assert not any("Raid enorme de chico" in t or "Raid enorme de kickero" in t for t in texts)


def _capture_ws():
    published = []
    bus = __import__("livevoice.core.bus", fromlist=["bus"]).bus
    bus.on("ws", lambda kind, data: published.append((kind, data)))
    return published


def test_each_action_can_have_its_own_gif(studio):
    studio.config.update({"alerts": {"follow": {"media": "C:/x/media/fiesta.gif", "duration": 7},
                                      "sub": {"media": "C:/x/media/sub.mp4"}}})
    published = _capture_ws()
    asyncio.run(studio.on_live_event(event(kind="follow", platform="tiktok", name="f1")))
    asyncio.run(studio.on_live_event(event(kind="sub", platform="twitch", name="s1")))
    asyncio.run(studio.on_live_event(event(kind="raid", amount=5, platform="twitch", name="r1")))
    alerts = {data["kind"]: data for kind, data in published if kind == "alert" and not data.get("custom")}
    assert alerts["follow"]["media"] == "/media/fiesta.gif" and alerts["follow"]["duration"] == 7
    assert alerts["sub"]["media"] == "/media/sub.mp4" and alerts["sub"]["media_type"] == "video"
    assert alerts["raid"]["media"] == ""


def test_command_with_only_gif(studio):
    studio.config.set("commands", [{"name": "!baile", "media": "C:/x/media/baile.gif", "cooldown": 0}])
    published = _capture_ws()
    asyncio.run(studio.on_live_event(event(text="!baile")))
    commands = [data for kind, data in published if kind == "command"]
    assert commands and commands[-1]["media"] == "/media/baile.gif"


def _rule(**values):
    base = {"id": values.get("name", "r"), "enabled": True, "replace_default": True, "overlay": False}
    return {**base, **values}


def test_platform_variants_pick_most_specific_rule(studio):
    studio.config.set("custom_alerts", [
        _rule(name="tt grandes", trigger="gift", platforms=["tiktok"], min_amount=1000, tts_text="grande"),
        _rule(name="tt galaxy", trigger="gift", platforms=["tiktok"], match="Galaxy", match_mode="exact", tts_text="galaxia exacta"),
        _rule(name="tw tier2", trigger="sub", platforms=["twitch"], match="Tier 2", match_mode="exact", tts_text="tier dos"),
        _rule(name="yt chico", trigger="gift", platforms=["youtube"], match="Super Chat", match_mode="exact", min_amount=1, max_amount=4, tts_text="sc chico"),
        _rule(name="yt grande", trigger="gift", platforms=["youtube"], match="Super Chat", match_mode="exact", min_amount=20, max_amount=99, tts_text="sc grande"),
        _rule(name="bits medianos", trigger="bits", platforms=["twitch"], min_amount=100, max_amount=999, tts_text="bits medianos"),
    ])
    run = lambda **kw: asyncio.run(studio.on_live_event(event(**kw)))
    run(kind="gift", gift="Galaxy", amount=1, value=1000, platform="tiktok", name="a")   # exacto gana al rango
    run(kind="gift", gift="Lion", amount=1, value=29999, platform="tiktok", name="b")    # solo el rango
    run(kind="gift", gift="Rose", amount=1, value=1, platform="tiktok", name="c")        # nada: alerta normal
    run(kind="sub", gift="Tier 2", platform="twitch", name="d")
    run(kind="sub", gift="Tier 1", platform="twitch", name="e")                          # alerta normal
    run(kind="gift", gift="Super Chat", amount=3, value=3, platform="youtube", name="f")
    run(kind="gift", gift="Super Chat", amount=50, value=50, platform="youtube", name="g")
    run(kind="gift", gift="Super Chat", amount=10, value=10, platform="youtube", name="h")  # entre rangos: normal
    run(kind="bits", amount=500, value=500, platform="twitch", name="i")
    run(kind="bits", amount=5000, value=5000, platform="twitch", name="j")              # fuera de rango: normal
    texts = spoken(studio)
    for expected in ("galaxia exacta", "grande", "tier dos", "sc chico", "sc grande", "bits medianos"):
        assert texts.count(expected) == 1, (expected, texts)
    assert any("envió 1 Rose" in t for t in texts)
    assert any("se suscribió" in t and t.startswith("¡e") for t in texts)
    assert any("envió 10 Super Chat" in t for t in texts)
    assert any("envió 5000 bits" in t for t in texts)


def test_gift_catalog_records_real_gifts_only(studio):
    asyncio.run(studio.on_live_event(event(kind="gift", gift="Hell Yeah", amount=1, value=10, platform="kick")))
    asyncio.run(studio._simulate("gift", {"platform": "kick", "gift": "Fake", "amount": 1, "value": 5}))
    kick = asyncio.run(studio.gift_catalog.for_platform("kick"))
    assert [gift["name"] for gift in kick] == ["Hell Yeah"]
