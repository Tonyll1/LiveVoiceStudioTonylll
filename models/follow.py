from dataclasses import dataclass

from models.user import User


@dataclass(slots=True)
class Follow:
    user: User