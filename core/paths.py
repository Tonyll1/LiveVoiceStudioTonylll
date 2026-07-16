from __future__ import annotations

import sys
from pathlib import Path


APP_NAME = "LiveVoice Studio"


def app_directory() -> Path:
    """Return the writable directory used by the portable application."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def data_path(*parts: str) -> Path:
    path = app_directory().joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_runtime_directories() -> None:
    for relative in (
        ("logs",),
        ("sounds", "cache"),
        ("sounds", "commands"),
    ):
        app_directory().joinpath(*relative).mkdir(parents=True, exist_ok=True)
