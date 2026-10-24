from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field


PLATFORMS = ("tiktok", "twitch", "kick", "youtube")


@dataclass(slots=True)
class User:
    platform: str
    id: str = ""
    username: str = ""
    display_name: str = ""
    avatar: str = ""
    color: str = ""
    is_moderator: bool = False
    is_subscriber: bool = False
    is_follower: bool = False
    is_broadcaster: bool = False
    is_vip: bool = False
    gifter_level: int = 0

    @property
    def name(self) -> str:
        return self.display_name or self.username or "Alguien"

    @property
    def key(self) -> str:
        """Identificador estable entre plataformas: 'twitch:usuario'."""
        return f"{self.platform}:{(self.username or self.id).lower()}"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["name"] = self.name
        data["key"] = self.key
        return data


@dataclass(slots=True)
class LiveEvent:
    """Evento normalizado de cualquier plataforma.

    kind: chat, follow, gift, sub, bits, raid, like, share, join
    """

    kind: str
    platform: str
    user: User
    text: str = ""
    amount: int = 1
    gift: str = ""
    value: int = 0
    image: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    tts_allowed: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "platform": self.platform,
            "user": self.user.to_dict(),
            "text": self.text,
            "amount": self.amount,
            "gift": self.gift,
            "value": self.value,
            "image": self.image,
            "timestamp": self.timestamp,
            "tts_allowed": self.tts_allowed,
        }
