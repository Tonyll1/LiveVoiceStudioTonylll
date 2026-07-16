from dataclasses import dataclass

from models.user import User


@dataclass(slots=True)
class Gift:
    user: User
    gift_name: str
    amount: int = 1