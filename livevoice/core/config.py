from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any

from livevoice.core.logger import logger
from livevoice.core.paths import data_path


DEFAULT_BOTS = [
    "nightbot", "streamelements", "streamlabs", "moobot", "fossabot",
    "wizebot", "botrix", "kickbot", "sery_bot", "soundalerts", "pokemoncommunitygame",
]


def _alert(text: str, *, tts: bool = True, min_amount: int = 1) -> dict:
    return {
        "enabled": True,
        "tts": tts,
        "overlay": True,
        "text": text,
        "sound": "",
        "min_amount": min_amount,
    }


DEFAULT_CONFIG: dict[str, Any] = {
    "general": {
        "port": 8765,
        "open_window": True,
        "first_run": True,
        "streamer_name": "",
    },
    "platforms": {
        "tiktok": {"enabled": True, "channel": "", "auto_connect": False, "sign_api_key": ""},
        "twitch": {"enabled": False, "channel": "", "auto_connect": False},
        "kick": {"enabled": False, "channel": "", "auto_connect": False},
        "youtube": {"enabled": False, "channel": "", "auto_connect": False},
    },
    "tts": {
        "enabled": True,
        "engine": "edge",
        "fallback_enabled": True,
        "voice": "es-MX-DaliaNeural",
        "rate": 0,
        "pitch": 0,
        "read_username": True,
        "template": "{user} dice: {message}",
        "read_platform": False,
        "max_length": 200,
        "max_queue": 25,
        "who": "everyone",
        "prefix": "",
        "random_voice_per_user": False,
        "random_voice_language": "es",
        "allow_voice_command": True,
        "user_voices": {},
        "user_cooldown": 0,
        "ignore_bots": True,
        "bots": DEFAULT_BOTS,
        "ignored_users": [],
        "skip_links": True,
        "read_emojis": False,
        "skip_commands": True,
        "replacements": {"xd": "equis de", "q": "que", "k": "que", "pq": "porque", "tqm": "te quiero mucho"},
        "read_events": {
            "follow": True,
            "gift": True,
            "sub": True,
            "raid": True,
            "share": False,
            "join": False,
        },
    },
    "moderation": {
        "filter_spam": True,
        "blocked_words": [],
        "blocked_mode": "replace",
    },
    "audio": {
        "output_device": "",
        "tts_volume": 100,
        "sfx_volume": 80,
    },
    "hotkeys": {
        "enabled": True,
        "toggle_mute": "ctrl+alt+m",
        "skip": "ctrl+alt+s",
        "clear_queue": "ctrl+alt+c",
        "pause": "ctrl+alt+p",
        "clip": "ctrl+alt+k",
    },
    "alerts": {
        "enabled": True,
        "follow": _alert("¡Gracias por el follow, {user}!"),
        "gift": _alert("¡{user} envió {amount} {gift}! Muchas gracias."),
        "sub": _alert("¡{user} se suscribió! Bienvenido a la familia."),
        "bits": _alert("¡{user} envió {amount} bits!"),
        "raid": _alert("¡Raid de {user} con {amount} personas! Bienvenidos."),
        "share": _alert("¡{user} compartió el directo!", tts=False),
        "like": _alert("¡Llegamos a {amount} likes!", min_amount=500),
        "join": {**_alert("{user} llegó al directo", tts=False), "enabled": False},
    },
    "commands": [],
    "games": {
        "enabled": True,
        "dice": True,
        "eightball": True,
        "love": True,
        "coin": True,
        "points_command": True,
        "top_command": True,
        "cooldown": 10,
    },
    "points": {
        "enabled": True,
        "name": "puntos",
        "per_message": 1,
        "per_follow": 20,
        "per_share": 10,
        "per_gift_coin": 5,
        "per_sub": 50,
    },
    "welcome": {
        "enabled": True,
        "text": "Bienvenido {user}, gracias por pasar.",
        "tts": True,
    },
    "timers": [
        {
            "enabled": False,
            "text": "Si te gusta el directo, sígueme y comparte para que llegue a más gente.",
            "interval_minutes": 10,
            "min_messages": 5,
        },
    ],
    "goals": {
        "likes": {"enabled": True, "title": "Meta de likes", "target": 1000},
        "followers": {"enabled": True, "title": "Meta de seguidores", "target": 20},
        "gifts": {"enabled": True, "title": "Meta de regalos", "target": 500},
        "subs": {"enabled": False, "title": "Meta de subs", "target": 5},
    },
    "obs": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 4455,
        "password": "",
        "clip_command": "!clip",
        "clip_permission": "moderators",
        "clip_cooldown": 60,
        "auto_clip_min_gift": 0,
    },
    "overlay": {
        "accent": "#8b5cf6",
        "chat_max": 8,
        "chat_fade_seconds": 0,
        "font_size": 22,
        "show_platform_icon": True,
    },
}


def deep_merge(base: dict, patch: dict) -> dict:
    """Mezcla `patch` sobre `base` (in-place) respetando diccionarios anidados."""
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _fill_defaults(data: dict, defaults: dict) -> bool:
    changed = False
    for key, value in defaults.items():
        if key not in data:
            data[key] = copy.deepcopy(value)
            changed = True
        elif isinstance(value, dict) and isinstance(data[key], dict) and key not in ("user_voices", "replacements"):
            changed = _fill_defaults(data[key], value) or changed
    return changed


class Config:
    def __init__(self, filename: Path | None = None):
        self.filename = Path(filename) if filename else data_path("config.json")
        self._lock = threading.RLock()
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict:
        data: dict[str, Any] = {}
        if self.filename.exists():
            try:
                data = json.loads(self.filename.read_text(encoding="utf-8"))
            except Exception as error:
                logger.error("config.json dañado, se crea una copia y se usan valores por defecto: %s", error)
                self.filename.replace(self.filename.with_suffix(".broken.json"))
                data = {}

        migrated = self._migrate_legacy(data)
        changed = _fill_defaults(data, DEFAULT_CONFIG) or migrated or not self.filename.exists()
        self.data = data
        if changed:
            self.save()
        return data

    def _migrate_legacy(self, data: dict) -> bool:
        """Convierte el config plano de las versiones 0.x al nuevo formato."""
        if "platforms" in data or not data:
            return False

        legacy = dict(data)
        data.clear()
        base = copy.deepcopy(DEFAULT_CONFIG)
        base["platforms"]["tiktok"]["channel"] = legacy.get("username", "")
        base["tts"]["voice"] = legacy.get("voice", base["tts"]["voice"])
        base["tts"]["read_events"]["gift"] = legacy.get("read_gifts", True)
        base["tts"]["read_events"]["follow"] = legacy.get("read_followers", True)
        base["tts"]["enabled"] = legacy.get("read_comments", True)
        base["moderation"]["filter_spam"] = legacy.get("filter_spam", True)
        base["moderation"]["blocked_words"] = legacy.get("blocked_words", [])
        base["moderation"]["blocked_mode"] = legacy.get("blocked_words_mode", "replace")

        legacy_commands = data_path("commands.json")
        if legacy_commands.exists():
            try:
                for item in json.loads(legacy_commands.read_text(encoding="utf-8")):
                    base["commands"].append({
                        "name": item.get("name", ""),
                        "type": "sound",
                        "sound": item.get("sound_path", ""),
                        "text": "",
                        "enabled": item.get("enabled", True),
                        "cooldown": item.get("cooldown_seconds", 30),
                        "permission": "allowlist" if item.get("permission") == "allowlist" else "everyone",
                        "allowed_users": item.get("allowed_users", []),
                    })
            except Exception as error:
                logger.warning("No se pudieron migrar los comandos antiguos: %s", error)

        data.update(base)
        logger.info("Configuración antigua migrada al formato 1.0")
        return True

    def save(self):
        with self._lock:
            temporary = self.filename.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary.replace(self.filename)

    def get(self, path: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, path: str, value: Any):
        with self._lock:
            parts = path.split(".")
            node = self.data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
            self.save()

    def update(self, patch: dict):
        with self._lock:
            deep_merge(self.data, patch)
            self.save()

    def snapshot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self.data)
