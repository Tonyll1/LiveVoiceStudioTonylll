from pathlib import Path

from models.command import Command
from models.comment import Comment
from models.user import User
from services.plugins.command_repository import CommandRepository
from services.plugins.command_service import CommandService


class FakeSoundAction:
    def __init__(self):
        self.played = []

    def execute(self, filename):
        self.played.append(str(filename))


def test_command_normalizes_name_and_users():
    command = Command(
        name=" Susto ",
        sound_path="sound.wav",
        permission="allowlist",
        allowed_users=["@Marco", "marco", " Ana "],
    )

    assert command.name == "!susto"
    assert command.allowed_users == ["ana", "marco"]
    assert command.is_allowed("@MARCO")
    assert not command.is_allowed("otro")


def test_repository_roundtrip(tmp_path):
    repository = CommandRepository(tmp_path / "commands.json")
    repository.save([Command("!hola", "hola.wav", cooldown_seconds=15)])

    commands = repository.load()

    assert len(commands) == 1
    assert commands[0].name == "!hola"
    assert commands[0].cooldown_seconds == 15


def test_service_executes_enabled_command(tmp_path):
    sound = tmp_path / "sound.wav"
    sound.write_bytes(b"fake")
    repository = CommandRepository(tmp_path / "commands.json")
    action = FakeSoundAction()
    service = CommandService(repository, action)
    service.save(Command("!susto", str(sound), cooldown_seconds=0))

    service.on_comment(Comment(User(username="viewer"), "!susto"))

    assert action.played == [str(sound)]


def test_service_respects_allowlist(tmp_path):
    sound = tmp_path / "sound.wav"
    sound.write_bytes(b"fake")
    repository = CommandRepository(tmp_path / "commands.json")
    action = FakeSoundAction()
    service = CommandService(repository, action)
    service.save(Command(
        "!vip",
        str(sound),
        cooldown_seconds=0,
        permission="allowlist",
        allowed_users=["marco"],
    ))

    service.on_comment(Comment(User(username="other"), "!vip"))
    service.on_comment(Comment(User(username="marco"), "!vip"))

    assert action.played == [str(sound)]
