"""Dinámicas para enganchar al chat: sorteos, encuestas, metas y mensajes automáticos."""
from __future__ import annotations

import asyncio
import random
import time

from livevoice.core.bus import bus
from livevoice.core.models import LiveEvent
from livevoice.features.chat_reader import user_matches
from livevoice.features.moderation import normalize
from livevoice.tts.manager import PRIORITY_ALERT, PRIORITY_EVENT, TTSManager


class Giveaway:
    def __init__(self, tts: TTSManager):
        self.tts = tts
        self.reset()

    def reset(self):
        self.active = False
        self.keyword = "!sorteo"
        self.prize = ""
        self.who = "everyone"
        self.entrants: dict[str, dict] = {}
        self.winner: dict | None = None

    def state(self) -> dict:
        return {
            "active": self.active,
            "keyword": self.keyword,
            "prize": self.prize,
            "who": self.who,
            "count": len(self.entrants),
            "entrants": list(self.entrants.values())[-60:],
            "winner": self.winner,
        }

    async def _publish(self, extra: dict | None = None):
        await bus.emit("ws", "giveaway", {**self.state(), **(extra or {})})

    async def start(self, keyword: str, prize: str = "", who: str = "everyone"):
        self.reset()
        self.active = True
        self.keyword = (keyword or "!sorteo").strip().lower()
        self.prize, self.who = prize.strip(), who
        prize_text = f" por {self.prize}" if self.prize else ""
        self.tts.say(f"¡Empieza el sorteo{prize_text}! Escribe {self.keyword} en el chat para participar.",
                     priority=PRIORITY_ALERT, force=True)
        await self._publish()

    async def stop(self):
        self.active = False
        await self._publish()

    async def on_chat(self, event: LiveEvent) -> bool:
        if not self.active or normalize(event.text).split(" ")[0] != normalize(self.keyword):
            return False
        if event.user.key in self.entrants or not user_matches(event, self.who):
            return True
        self.entrants[event.user.key] = {
            "key": event.user.key, "name": event.user.name, "platform": event.platform, "avatar": event.user.avatar,
        }
        await self._publish()
        return True

    async def draw(self) -> dict | None:
        self.active = False
        if not self.entrants:
            self.tts.say("No hay participantes en el sorteo.", priority=PRIORITY_ALERT, force=True)
            await self._publish()
            return None
        self.winner = random.choice(list(self.entrants.values()))
        names = [entrant["name"] for entrant in self.entrants.values()]
        await self._publish({"rolling": names[:40]})
        await asyncio.sleep(4)
        self.tts.say(f"¡Felicidades {self.winner['name']}! Ganaste el sorteo.", priority=PRIORITY_ALERT, force=True)
        await self._publish({"announce": True})
        return self.winner


class Poll:
    def __init__(self, tts: TTSManager):
        self.tts = tts
        self.reset()
        self._timer: asyncio.Task | None = None

    def reset(self):
        self.active = False
        self.question = ""
        self.options: list[str] = []
        self.votes: dict[str, int] = {}
        self.ends_at = 0.0

    def results(self) -> list[dict]:
        totals = [0] * len(self.options)
        for choice in self.votes.values():
            totals[choice] += 1
        total = sum(totals) or 1
        return [
            {"option": option, "votes": totals[index], "percent": round(totals[index] * 100 / total)}
            for index, option in enumerate(self.options)
        ]

    def state(self) -> dict:
        return {
            "active": self.active,
            "question": self.question,
            "results": self.results(),
            "total": len(self.votes),
            "remaining": max(0, int(self.ends_at - time.time())) if self.active else 0,
        }

    async def _publish(self):
        await bus.emit("ws", "poll", self.state())

    async def start(self, question: str, options: list[str], duration: int = 60):
        options = [option.strip() for option in options if option.strip()][:6]
        if len(options) < 2:
            raise ValueError("La encuesta necesita al menos 2 opciones.")
        self.reset()
        self.active = True
        self.question, self.options = question.strip(), options
        self.ends_at = time.time() + max(10, duration)
        listing = ", ".join(f"{index + 1} para {option}" for index, option in enumerate(options))
        self.tts.say(f"Encuesta: {self.question}. Escribe {listing}.", priority=PRIORITY_ALERT, force=True)
        if self._timer:
            self._timer.cancel()
        self._timer = asyncio.create_task(self._countdown())
        await self._publish()

    async def _countdown(self):
        while self.active and time.time() < self.ends_at:
            await asyncio.sleep(1)
            await self._publish()
        if self.active:
            await self.finish()

    async def finish(self):
        if not self.active:
            return
        self.active = False
        results = self.results()
        if self.votes:
            best = max(results, key=lambda item: item["votes"])
            self.tts.say(f"Terminó la encuesta. Ganó {best['option']} con {best['percent']} por ciento.",
                         priority=PRIORITY_ALERT, force=True)
        await self._publish()

    async def on_chat(self, event: LiveEvent) -> bool:
        if not self.active:
            return False
        text = event.text.strip().lower().removeprefix("!votar").removeprefix("!vote").strip()
        if text.isdigit() and 1 <= int(text) <= len(self.options):
            self.votes[event.user.key] = int(text) - 1
            await self._publish()
            return True
        return False


class Goals:
    KIND_FOR_EVENT = {"like": "likes", "follow": "followers", "gift": "gifts", "bits": "gifts", "sub": "subs"}

    def __init__(self, config, tts: TTSManager, stats):
        self.config = config
        self.tts = tts
        self.stats = stats
        self.offsets = {"likes": 0, "followers": 0, "gifts": 0, "subs": 0}
        self.celebrated: set[str] = set()

    def current(self, goal: str) -> int:
        value = {
            "likes": self.stats.likes,
            "followers": self.stats.followers,
            "gifts": self.stats.gift_value,
            "subs": self.stats.subs,
        }[goal]
        return max(0, value - self.offsets[goal])

    def state(self) -> dict:
        goals = self.config.get("goals")
        return {
            name: {**settings, "current": self.current(name)}
            for name, settings in goals.items()
        }

    def reset(self, goal: str):
        self.offsets[goal] = self.offsets[goal] + self.current(goal)
        self.celebrated.discard(goal)

    async def publish(self):
        await bus.emit("ws", "goals", self.state())

    async def on_event(self, event: LiveEvent):
        goal = self.KIND_FOR_EVENT.get(event.kind)
        if not goal:
            return
        settings = self.config.get(f"goals.{goal}")
        await self.publish()
        if not settings.get("enabled") or goal in self.celebrated:
            return
        if self.current(goal) >= int(settings.get("target", 0) or 0) > 0:
            self.celebrated.add(goal)
            self.tts.say(f"¡Meta cumplida! {settings.get('title', '')}. ¡Muchas gracias a todos!",
                         priority=PRIORITY_ALERT, force=True)
            await bus.emit("ws", "alert", {
                "kind": "goal", "title": "¡Meta cumplida!", "text": settings.get("title", ""), "user": {"name": ""},
            })


class Timers:
    """Mensajes leídos cada X minutos, solo si hubo actividad en el chat (no habla sola en un directo vacío)."""

    def __init__(self, config, tts: TTSManager):
        self.config = config
        self.tts = tts
        self.messages_since: dict[int, int] = {}
        self.last_run: dict[int, float] = {}
        self._task: asyncio.Task | None = None

    def start(self):
        self._task = asyncio.create_task(self._loop())

    def on_chat(self):
        for index in range(len(self.config.get("timers", []))):
            self.messages_since[index] = self.messages_since.get(index, 0) + 1

    async def _loop(self):
        while True:
            await asyncio.sleep(15)
            now = time.time()
            for index, timer in enumerate(self.config.get("timers", [])):
                if not timer.get("enabled") or not timer.get("text"):
                    continue
                interval = max(1, int(timer.get("interval_minutes", 10))) * 60
                last = self.last_run.setdefault(index, now)
                if now - last >= interval and self.messages_since.get(index, 0) >= int(timer.get("min_messages", 0)):
                    self.last_run[index] = now
                    self.messages_since[index] = 0
                    self.tts.say(timer["text"], priority=PRIORITY_EVENT)
                    await bus.emit("ws", "notice", {"level": "info", "text": f"Mensaje automático: {timer['text'][:60]}"})
