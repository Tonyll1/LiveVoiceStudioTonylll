"""Estadísticas de la sesión actual y datos persistentes de espectadores."""
from __future__ import annotations

import json
import threading
import time
from collections import Counter, deque

from livevoice.core.models import LiveEvent
from livevoice.core.paths import data_path


class ViewerStore:
    """Puntos y datos de espectadores, persistidos en data/viewers.json."""

    def __init__(self):
        self.filename = data_path("data", "viewers.json")
        self._lock = threading.RLock()
        self._dirty = False
        self.viewers: dict[str, dict] = {}
        if self.filename.exists():
            try:
                self.viewers = json.loads(self.filename.read_text(encoding="utf-8"))
            except Exception:
                self.viewers = {}

    def touch(self, event: LiveEvent) -> dict:
        user = event.user
        with self._lock:
            viewer = self.viewers.setdefault(user.key, {
                "name": user.name,
                "platform": user.platform,
                "points": 0,
                "messages": 0,
                "first_seen": time.time(),
            })
            viewer["name"] = user.name
            viewer["last_seen"] = time.time()
            self._dirty = True
            return viewer

    def add_points(self, key: str, amount: int):
        if amount == 0:
            return
        with self._lock:
            if key in self.viewers:
                self.viewers[key]["points"] = max(0, self.viewers[key].get("points", 0) + amount)
                self._dirty = True

    def get(self, key: str) -> dict | None:
        return self.viewers.get(key)

    def top(self, limit: int = 10) -> list[dict]:
        with self._lock:
            ranked = sorted(self.viewers.items(), key=lambda item: -item[1].get("points", 0))
            return [{"key": key, **data} for key, data in ranked[:limit]]

    def flush(self):
        with self._lock:
            if not self._dirty:
                return
            temporary = self.filename.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.viewers, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self.filename)
            self._dirty = False


class SessionStats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.started_at = time.time()
        self.messages = 0
        self.likes = 0
        self.followers = 0
        self.shares = 0
        self.subs = 0
        self.gift_value = 0
        self.gifts = 0
        self.chatters: set[str] = set()
        self.gifters: Counter[str] = Counter()
        self.gifter_names: dict[str, str] = {}
        self.chat_counter: Counter[str] = Counter()
        self.recent: deque[dict] = deque(maxlen=300)

    def register(self, event: LiveEvent) -> bool:
        """Actualiza contadores. Devuelve True si es la primera vez que el usuario habla."""
        first_message = False
        key = event.user.key
        if event.kind == "chat":
            self.messages += 1
            self.chat_counter[key] += 1
            first_message = key not in self.chatters
            self.chatters.add(key)
        elif event.kind == "like":
            self.likes += event.amount
        elif event.kind == "follow":
            self.followers += 1
        elif event.kind == "share":
            self.shares += 1
        elif event.kind == "sub":
            self.subs += max(1, event.amount)
        elif event.kind in ("gift", "bits"):
            value = event.value or event.amount
            self.gifts += event.amount
            self.gift_value += value
            self.gifters[key] += value
            self.gifter_names[key] = event.user.name

        if event.kind not in ("like", "join"):
            self.recent.append(event.to_dict())
        return first_message

    def top_gifters(self, limit: int = 5) -> list[dict]:
        return [
            {"key": key, "name": self.gifter_names.get(key, key), "value": value}
            for key, value in self.gifters.most_common(limit)
        ]

    def to_dict(self) -> dict:
        return {
            "uptime": int(time.time() - self.started_at),
            "messages": self.messages,
            "likes": self.likes,
            "followers": self.followers,
            "shares": self.shares,
            "subs": self.subs,
            "gifts": self.gifts,
            "gift_value": self.gift_value,
            "chatters": len(self.chatters),
            "top_gifters": self.top_gifters(),
        }
