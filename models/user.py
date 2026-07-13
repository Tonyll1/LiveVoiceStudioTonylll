from dataclasses import dataclass


@dataclass(slots=True)
class User:
    id: str | None = None
    username: str = ""
    nickname: str = ""
    photo: str | None = None