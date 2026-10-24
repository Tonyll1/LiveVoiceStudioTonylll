"""Atajos de teclado globales (funcionan aunque estés dentro del juego)."""
from __future__ import annotations

from typing import Callable

from livevoice.core.logger import logger

try:
    import keyboard
except Exception:  # pragma: no cover - depende del sistema
    keyboard = None


ACTIONS = {
    "toggle_mute": "Silenciar / activar voz",
    "skip": "Saltar mensaje actual",
    "clear_queue": "Vaciar cola",
    "pause": "Pausar / reanudar voz",
    "clip": "Guardar clip",
}


class Hotkeys:
    def __init__(self, config, dispatch: Callable[[str], None]):
        self.config = config
        self.dispatch = dispatch
        self.registered: dict[str, str] = {}
        self.errors: dict[str, str] = {}

    @property
    def available(self) -> bool:
        return keyboard is not None

    def apply(self):
        self.clear()
        if keyboard is None:
            self.errors["_"] = "La librería 'keyboard' no está instalada."
            return
        settings = self.config.get("hotkeys")
        if not settings.get("enabled", True):
            return
        for action in ACTIONS:
            combo = (settings.get(action) or "").strip()
            if not combo:
                continue
            try:
                keyboard.add_hotkey(combo, self.dispatch, args=(action,), suppress=False)
                self.registered[action] = combo
            except Exception as error:
                self.errors[action] = str(error)
                logger.warning("Atajo inválido %s=%s: %s", action, combo, error)

    def clear(self):
        self.errors = {}
        if keyboard is not None and self.registered:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
        self.registered = {}

    def state(self) -> dict:
        return {"available": self.available, "registered": self.registered, "errors": self.errors, "actions": ACTIONS}
