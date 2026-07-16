import time
from pathlib import Path
from typing import Protocol

from core.constants import (
    COMMAND_BLOCKED_EVENT,
    COMMAND_TRIGGERED_EVENT,
    COMMENT_EVENT,
    ERROR_EVENT,
)
from core.event_bus import event_bus
from core.events import Priority
from models.command import Command
from models.comment import Comment
from services.plugins.command_repository import CommandRepository


class SoundExecutor(Protocol):
    def execute(self, filename: str | Path): ...


class CommandService:
    def __init__(
        self,
        repository: CommandRepository,
        sound_action: SoundExecutor,
    ):
        self.repository = repository
        self.sound_action = sound_action
        self._commands: dict[str, Command] = {}
        self._last_execution: dict[tuple[str, str], float] = {}
        self.reload()

        event_bus.subscribe(
            COMMENT_EVENT,
            self.on_comment,
            priority=Priority.HIGH,
        )

    def reload(self):
        self._commands = {
            command.name: command
            for command in self.repository.load()
        }

    def list_commands(self) -> list[Command]:
        return sorted(self._commands.values(), key=lambda command: command.name)

    def get(self, name: str) -> Command | None:
        return self._commands.get(Command.normalize_name(name))

    def save(self, command: Command, previous_name: str | None = None):
        if command.name == "!":
            raise ValueError("Escribe un nombre de comando válido.")
        if not command.sound_path:
            raise ValueError("Selecciona un archivo de sonido.")
        if not Path(command.sound_path).is_file():
            raise FileNotFoundError("El archivo de sonido seleccionado no existe.")

        if previous_name:
            old_name = Command.normalize_name(previous_name)
            if old_name != command.name:
                self._commands.pop(old_name, None)

        self._commands[command.name] = command
        self._persist()

    def delete(self, name: str):
        self._commands.pop(Command.normalize_name(name), None)
        self._persist()

    def set_enabled(self, name: str, enabled: bool):
        command = self.get(name)
        if command is None:
            raise KeyError(f"Comando no encontrado: {name}")
        command.enabled = bool(enabled)
        self._persist()

    def test(self, name: str):
        command = self.get(name)
        if command is None:
            raise KeyError(f"Comando no encontrado: {name}")
        self.sound_action.execute(command.sound_path)

    def on_comment(self, comment: Comment, _read_tts: bool = True):
        command_name = self._extract_command(comment.text)
        if command_name is None:
            return

        command = self._commands.get(command_name)
        if command is None or not command.enabled:
            return

        username = comment.user.username or comment.user.nickname or ""
        if not command.is_allowed(username):
            event_bus.emit(COMMAND_BLOCKED_EVENT, command, comment.user, "permission")
            return

        cooldown_key = (command.name, username.lower())
        remaining = self._remaining_cooldown(command, cooldown_key)
        if remaining > 0:
            event_bus.emit(COMMAND_BLOCKED_EVENT, command, comment.user, "cooldown", remaining)
            return

        try:
            self.sound_action.execute(command.sound_path)
            self._last_execution[cooldown_key] = time.monotonic()
            event_bus.emit(COMMAND_TRIGGERED_EVENT, command, comment.user)
        except Exception as error:
            event_bus.emit(ERROR_EVENT, f"No se pudo ejecutar {command.name}: {error}")

    @staticmethod
    def _extract_command(text: str) -> str | None:
        first_word = text.strip().split(maxsplit=1)[0].lower() if text.strip() else ""
        if not first_word.startswith("!") or first_word == "!":
            return None
        return first_word

    def _remaining_cooldown(self, command: Command, key: tuple[str, str]) -> int:
        last_execution = self._last_execution.get(key)
        if last_execution is None:
            return 0

        elapsed = time.monotonic() - last_execution
        return max(0, int(command.cooldown_seconds - elapsed + 0.999))

    def _persist(self):
        self.repository.save(self.list_commands())
