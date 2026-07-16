import json
from pathlib import Path

from core.logger import logger
from core.paths import data_path
from models.command import Command


class CommandRepository:
    def __init__(self, filename: str | Path | None = None):
        self.filename = Path(filename) if filename is not None else data_path("commands.json")

    def load(self) -> list[Command]:
        if not self.filename.exists():
            return []

        try:
            with self.filename.open("r", encoding="utf-8") as file:
                raw_commands = json.load(file)

            if not isinstance(raw_commands, list):
                raise ValueError("commands.json debe contener una lista.")

            commands = []
            for item in raw_commands:
                if not isinstance(item, dict):
                    continue
                command = Command.from_dict(item)
                if command.name != "!":
                    commands.append(command)
            return commands
        except Exception as error:
            logger.exception("No se pudieron cargar los comandos: %s", error)
            return []

    def save(self, commands: list[Command]):
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.filename.with_suffix(".tmp")

        with temporary.open("w", encoding="utf-8") as file:
            json.dump(
                [command.to_dict() for command in commands],
                file,
                indent=4,
                ensure_ascii=False,
            )

        temporary.replace(self.filename)
