from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class Command:
    name: str
    sound_path: str
    enabled: bool = True
    cooldown_seconds: int = 30
    permission: str = "everyone"
    allowed_users: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.name = self.normalize_name(self.name)
        self.sound_path = self.sound_path.strip()
        self.cooldown_seconds = max(0, int(self.cooldown_seconds))
        self.permission = (
            self.permission
            if self.permission in {"everyone", "allowlist"}
            else "everyone"
        )
        self.allowed_users = sorted({
            username.strip().lower().replace("@", "")
            for username in self.allowed_users
            if username.strip()
        })

    @staticmethod
    def normalize_name(name: str) -> str:
        normalized = name.strip().lower()
        if not normalized.startswith("!"):
            normalized = f"!{normalized}"
        return normalized

    def is_allowed(self, username: str) -> bool:
        if self.permission == "everyone":
            return True
        return username.strip().lower().replace("@", "") in self.allowed_users

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Command":
        return cls(
            name=data.get("name", ""),
            sound_path=data.get("sound_path", ""),
            enabled=bool(data.get("enabled", True)),
            cooldown_seconds=data.get("cooldown_seconds", 30),
            permission=data.get("permission", "everyone"),
            allowed_users=list(data.get("allowed_users", [])),
        )
