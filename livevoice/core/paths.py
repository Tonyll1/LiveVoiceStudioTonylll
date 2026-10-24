from __future__ import annotations

import sys
from pathlib import Path


def app_directory() -> Path:
    """Carpeta escribible: junto al .exe en modo portable o la raíz del proyecto."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_directory() -> Path:
    """Carpeta de recursos de solo lectura (web/, assets/). En PyInstaller vive en _MEIPASS."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", app_directory()))
    return Path(__file__).resolve().parents[2]


def data_path(*parts: str) -> Path:
    path = app_directory().joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(*parts: str) -> Path:
    return resource_directory().joinpath(*parts)


def ensure_runtime_directories() -> None:
    for relative in (
        ("logs",),
        ("data",),
        ("sounds", "cache"),
        ("sounds", "commands"),
        ("sounds", "alerts"),
        ("clips",),
    ):
        app_directory().joinpath(*relative).mkdir(parents=True, exist_ok=True)
