import sys
import types

if "edge_tts" not in sys.modules:
    sys.modules["edge_tts"] = types.SimpleNamespace()

from services.tts.voices import Voice, VoiceCatalog


def make_catalog() -> VoiceCatalog:
    catalog = VoiceCatalog()
    catalog._voices = [
        Voice("es-MX-DaliaNeural", "es-MX", "es", "MX", "Female", "Dalia"),
        Voice("es-MX-JorgeNeural", "es-MX", "es", "MX", "Male", "Jorge"),
        Voice("en-US-JennyNeural", "en-US", "en", "US", "Female", "Jenny"),
    ]
    return catalog


def test_random_voice_respects_language():
    catalog = make_catalog()

    for _ in range(20):
        selected = catalog.choose_random(language="en")
        assert selected is not None
        assert selected.language == "en"


def test_random_voice_avoids_immediate_repeat_when_possible():
    catalog = make_catalog()

    selected = catalog.choose_random(
        language="es",
        exclude_voice_id="es-MX-DaliaNeural",
    )

    assert selected is not None
    assert selected.short_name == "es-MX-JorgeNeural"

def test_random_voice_returns_none_for_empty_pool():
    catalog = make_catalog()
    assert catalog.choose_random(language="ja") is None
