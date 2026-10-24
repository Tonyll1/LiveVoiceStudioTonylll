"""Comandos del chat: los personalizados (sonidos / frases) y los integrados (voces, juegos, mods)."""
from __future__ import annotations

import random
import time
from pathlib import Path

from livevoice.core.bus import bus
from livevoice.core.logger import logger
from livevoice.core.models import LiveEvent
from livevoice.features.chat_reader import user_matches
from livevoice.tts.manager import PRIORITY_EVENT
from livevoice.tts.text import clean_for_speech, render
from livevoice.tts.voices import PRESETS, VOICE_ALIASES


EIGHT_BALL = [
    "Sí, definitivamente.", "Sin duda.", "Lo veo muy probable.", "Pregunta de nuevo más tarde.",
    "Mejor no te lo digo ahora.", "No cuentes con ello.", "Mis fuentes dicen que no.", "Muy dudoso.",
    "Claro que sí, campeón.", "Ni lo sueñes.", "Las estrellas dicen que sí.", "Eso es un misterio.",
]


def normalize_command(name: str) -> str:
    name = name.strip().lower()
    return name if name.startswith("!") else f"!{name}"


class Commands:
    def __init__(self, app):
        self.app = app
        self.config = app.config
        self._cooldowns: dict[tuple[str, str], float] = {}

    # ── Utilidades ─────────────────────────────────────────────────

    def _on_cooldown(self, scope: str, user_key: str, seconds: int) -> bool:
        if seconds <= 0:
            return False
        key = (scope, user_key)
        now = time.monotonic()
        if now - self._cooldowns.get(key, 0) < seconds:
            return True
        self._cooldowns[key] = now
        return False

    def _say(self, text: str, event: LiveEvent | None = None):
        self.app.tts.say(
            text,
            priority=PRIORITY_EVENT,
            user_key=event.user.key if event else "",
            user_name=event.user.name if event else "",
            platform=event.platform if event else "",
        )

    @staticmethod
    def _allowed(event: LiveEvent, permission: str, allowed_users: list[str]) -> bool:
        if permission == "allowlist":
            name = (event.user.username or "").lower().lstrip("@")
            return event.user.is_broadcaster or name in {user.lower().lstrip("@") for user in allowed_users}
        return user_matches(event, permission)

    # ── Entrada ────────────────────────────────────────────────────

    async def handle(self, event: LiveEvent) -> bool:
        """Devuelve True si el mensaje era un comando (y por tanto no se lee como chat)."""
        text = event.text.strip()
        if not text.startswith("!"):
            return False
        name, _, args = text.partition(" ")
        name, args = name.lower(), args.strip()

        for command in self.config.get("commands", []):
            if command.get("enabled", True) and normalize_command(command.get("name", "")) == name:
                await self._run_custom(command, event, args)
                return True

        if name == normalize_command(self.config.get("obs.clip_command", "!clip")):
            await self.clip_from_chat(event, args)
            return True

        handler = getattr(self, f"_builtin_{name[1:]}", None)
        aliases = {"!voice": "!voz", "!points": "!puntos", "!dice": "!dado", "!8ball": "!bola", "!coin": "!moneda",
                   "!love": "!amor", "!saltar": "!skip", "!callar": "!mute", "!ranking": "!top"}
        if handler is None and name in aliases:
            handler = getattr(self, f"_builtin_{aliases[name][1:]}", None)
        if handler is not None:
            await handler(event, args)
            return True
        return False

    async def _run_custom(self, command: dict, event: LiveEvent, args: str):
        if not self._allowed(event, command.get("permission", "everyone"), command.get("allowed_users", [])):
            return
        name = normalize_command(command["name"])
        if self._on_cooldown(f"global:{name}", "*", int(command.get("global_cooldown", 0) or 0)):
            return
        if not event.user.is_broadcaster and self._on_cooldown(name, event.user.key, int(command.get("cooldown", 0) or 0)):
            await bus.emit("ws", "notice", {"level": "info", "text": f"{event.user.name} usó {name} en cooldown."})
            return

        sound = command.get("sound", "")
        if sound:
            if Path(sound).is_file():
                try:
                    self.app.player.play_effect(sound, int(command.get("volume", 100)))
                except Exception as error:
                    logger.warning("Comando %s: %s", name, error)
            else:
                await bus.emit("ws", "notice", {"level": "warning", "text": f"El sonido de {name} no existe: {sound}"})

        text = command.get("text", "")
        if text:
            target = args.lstrip("@") or event.user.name
            self._say(render(text, user=event.user.name, target=target, args=args, points=self._points(event)), event)

        await bus.emit("ws", "command", {"name": name, "user": event.user.to_dict(), "platform": event.platform})

    def _points(self, event: LiveEvent) -> int:
        viewer = self.app.viewers.get(event.user.key) or {}
        return int(viewer.get("points", 0))

    # ── Integrados ─────────────────────────────────────────────────

    async def _builtin_voz(self, event: LiveEvent, args: str):
        if not self.config.get("tts.allow_voice_command", True) or not args:
            return
        if self._on_cooldown("!voz", event.user.key, 20):
            return
        voices = dict(self.config.get("tts.user_voices", {}))
        current = dict(voices.get(event.user.key, {}))
        if args.lower() in ("normal", "reset", "quitar"):
            voices.pop(event.user.key, None)
            self.config.set("tts.user_voices", voices)
            self._say(f"{event.user.name} vuelve a la voz normal.", event)
            return
        if args.lower() in ("random", "aleatoria", "azar"):
            choice = random.choice(list(VOICE_ALIASES.values()))
            current["voice"] = choice
        else:
            voice_id, preset_id = self.app.catalog.resolve_alias(args)
            if voice_id is None and preset_id is None:
                return
            if voice_id:
                current["voice"] = voice_id
            if preset_id:
                current["preset"] = preset_id
        voices[event.user.key] = current
        self.config.set("tts.user_voices", voices)
        self._say(f"{event.user.name}, esta es tu nueva voz.", event)

    async def _builtin_voces(self, event: LiveEvent, _args: str):
        if self._on_cooldown("!voces", "*", 60):
            return
        presets = ", ".join(preset["name"].lower() for preset in PRESETS[1:6])
        self._say(f"Usa voz seguido de: mexicano, argentino, gringo, japonés, o {presets}.")

    async def _builtin_puntos(self, event: LiveEvent, _args: str):
        if not self.config.get("games.points_command", True) or not self.config.get("points.enabled", True):
            return
        if self._on_cooldown("!puntos", event.user.key, 30):
            return
        self._say(f"{event.user.name} tiene {self._points(event)} {self.config.get('points.name', 'puntos')}.")

    async def _builtin_top(self, event: LiveEvent, _args: str):
        if not self.config.get("games.top_command", True) or self._on_cooldown("!top", "*", 60):
            return
        top = self.app.viewers.top(3)
        if top:
            listing = ", ".join(f"{index + 1}, {clean_for_speech(item['name'], max_length=30)}" for index, item in enumerate(top))
            self._say(f"Top del canal: {listing}.")

    def _game_allowed(self, game: str, event: LiveEvent) -> bool:
        games = self.config.get("games")
        if not games.get("enabled", True) or not games.get(game, True):
            return False
        return not self._on_cooldown(f"game:{game}", event.user.key, int(games.get("cooldown", 10)))

    async def _builtin_dado(self, event: LiveEvent, _args: str):
        if self._game_allowed("dice", event):
            self._say(f"{event.user.name} lanzó el dado y sacó un {random.randint(1, 6)}.")

    async def _builtin_moneda(self, event: LiveEvent, _args: str):
        if self._game_allowed("coin", event):
            self._say(f"{event.user.name} lanzó una moneda: salió {random.choice(['cara', 'cruz'])}.")

    async def _builtin_bola(self, event: LiveEvent, args: str):
        if args and self._game_allowed("eightball", event):
            question = clean_for_speech(args, max_length=80)
            self._say(f"{event.user.name} pregunta: {question}. La bola mágica dice: {random.choice(EIGHT_BALL)}")

    async def _builtin_amor(self, event: LiveEvent, args: str):
        if args and self._game_allowed("love", event):
            target = clean_for_speech(args.lstrip("@"), max_length=30)
            score = random.Random(f"{event.user.key}|{target.lower()}").randint(0, 100)
            self._say(f"Entre {event.user.name} y {target} hay un {score} por ciento de amor.")

    # ── Moderadores ────────────────────────────────────────────────

    async def _builtin_skip(self, event: LiveEvent, _args: str):
        if event.user.is_moderator or event.user.is_broadcaster:
            self.app.tts.skip()

    async def _builtin_mute(self, event: LiveEvent, _args: str):
        if event.user.is_moderator or event.user.is_broadcaster:
            self.app.tts.toggle_mute()

    async def _builtin_clip(self, event: LiveEvent, args: str):
        configured = normalize_command(self.config.get("obs.clip_command", "!clip"))
        if configured != "!clip":
            return
        await self.clip_from_chat(event, args)

    async def clip_from_chat(self, event: LiveEvent, args: str):
        permission = self.config.get("obs.clip_permission", "moderators")
        if not user_matches(event, permission):
            return
        reason = f"{event.user.name}: {args}" if args else f"pedido por {event.user.name}"
        result = await self.app.obs.clip(reason, respect_cooldown=not event.user.is_broadcaster)
        if result.get("ok"):
            self._say("Clip guardado.")
