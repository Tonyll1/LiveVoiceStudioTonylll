"""Limpieza del texto antes de leerlo en voz alta."""
from __future__ import annotations

import re

URL_RE = re.compile(r"(https?://\S+|www\.\S+|\b\S+\.(com|net|org|gg|tv|ly|io|me|xyz)\S*)", re.IGNORECASE)
REPEAT_RE = re.compile(r"(\w)\1{2,}", re.UNICODE)
KICK_EMOTE_RE = re.compile(r"\[emote:\d+:([^\]]+)\]")
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF‍️←-⇿⬀-⯿]+",
    flags=re.UNICODE,
)
LAUGH_RE = re.compile(r"\b(?:j+a+){2,}j*\b|\b(?:j+e+){2,}j*\b", re.IGNORECASE)


def clean_for_speech(
    text: str,
    *,
    skip_links: bool = True,
    read_emojis: bool = False,
    replacements: dict[str, str] | None = None,
    max_length: int = 200,
) -> str:
    text = KICK_EMOTE_RE.sub(lambda match: match.group(1), text)
    if skip_links:
        text = URL_RE.sub(" un enlace ", text)
    if not read_emojis:
        text = EMOJI_RE.sub(" ", text)
    text = REPEAT_RE.sub(lambda match: match.group(1) * 2, text)
    text = LAUGH_RE.sub("jajaja", text)

    if replacements:
        for source, target in replacements.items():
            if source:
                text = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", target, text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    if max_length and len(text) > max_length:
        cut = text[:max_length].rsplit(" ", 1)[0]
        text = cut or text[:max_length]
    return text


def render(template: str, **values) -> str:
    """Formatea plantillas tipo '{user} dice: {message}' sin romperse si falta una clave."""

    class _Safe(dict):
        def __missing__(self, key):
            return ""

    try:
        return template.format_map(_Safe(values)).strip()
    except (ValueError, IndexError):
        return template
