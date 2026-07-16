from dataclasses import dataclass

from models.user import User


@dataclass(slots=True)
class Like:
    user: User
    count: int = 1