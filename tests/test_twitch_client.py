from services.twitch.client import TwitchClient


class DummyConfig:
    def get(self, _key, default=None):
        return default


def test_normalize_twitch_channel():
    assert TwitchClient._normalize_channel("#Canal") == "canal"
    assert TwitchClient._normalize_channel("https://www.twitch.tv/Canal/") == "canal"


def test_parse_and_unescape_twitch_tags():
    tags, remainder = TwitchClient._split_tags(
        "@display-name=Marco\\sVG;user-id=123 :marco!marco@host PRIVMSG #canal :hola"
    )
    assert tags["user-id"] == "123"
    assert TwitchClient._unescape_tag(tags["display-name"]) == "Marco VG"
    assert remainder.startswith(":marco!")


def test_twitch_client_starts_disconnected():
    client = TwitchClient(DummyConfig())
    assert client.connected is False
    assert client.channel == ""
