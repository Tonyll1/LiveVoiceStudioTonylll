from models.comment import Comment
from models.user import User
from services.tiktok.filters import MessageFilter
from services.tts.formatter import Formatter


class FakeConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


def make_comment(text="Hola"):
    return Comment(
        user=User(
            id="1",
            username="marco",
            nickname="Marco",
            photo=None,
        ),
        text=text,
    )


def test_formatter_can_read_username():
    assert Formatter.comment(make_comment()) == "Marco dice: Hola"


def test_formatter_can_omit_username():
    assert Formatter.comment(
        make_comment(),
        include_username=False,
    ) == "Hola"


def test_emoji_spam_is_blocked_when_enabled():
    message_filter = MessageFilter(
        FakeConfig({
            "filter_spam": False,
            "filter_emoji_spam": True,
        })
    )

    show, read_tts, _ = message_filter.process("1", "😂😂😂😂😂😂")

    assert show is False
    assert read_tts is False


def test_emoji_spam_can_be_disabled():
    message_filter = MessageFilter(
        FakeConfig({
            "filter_spam": False,
            "filter_emoji_spam": False,
        })
    )

    show, read_tts, text = message_filter.process("1", "😂😂😂😂😂😂")

    assert show is True
    assert read_tts is True
    assert text == "😂😂😂😂😂😂"


def test_normal_text_with_emoji_is_allowed():
    message_filter = MessageFilter(
        FakeConfig({
            "filter_spam": False,
            "filter_emoji_spam": True,
        })
    )

    show, read_tts, text = message_filter.process(
        "1",
        "Qué buen directo 😂",
    )

    assert show is True
    assert read_tts is True
    assert text == "Qué buen directo 😂"


def test_ascii_art_is_blocked_when_enabled():
    message_filter = MessageFilter(
        FakeConfig({
            "filter_spam": False,
            "filter_emoji_spam": False,
            "filter_ascii_art": True,
        })
    )

    show, read_tts, _ = message_filter.process(
        "1",
        "┏━━━━━━━━━━━━┓",
    )

    assert show is False
    assert read_tts is False


def test_ascii_art_can_be_disabled():
    message_filter = MessageFilter(
        FakeConfig({
            "filter_spam": False,
            "filter_emoji_spam": False,
            "filter_ascii_art": False,
        })
    )

    show, read_tts, text = message_filter.process(
        "1",
        "┏━━━━━━━━━━━━┓",
    )

    assert show is True
    assert read_tts is True
    assert text == "┏━━━━━━━━━━━━┓"


def test_normal_punctuation_is_not_ascii_art():
    message_filter = MessageFilter(
        FakeConfig({
            "filter_spam": False,
            "filter_emoji_spam": False,
            "filter_ascii_art": True,
        })
    )

    show, read_tts, text = message_filter.process(
        "1",
        "¡Hola, qué buen directo!!!",
    )

    assert show is True
    assert read_tts is True
    assert text == "¡Hola, qué buen directo!!!"
