"""Chat de Twitch por IRC anónimo (solo lectura, no necesita cuenta ni token)."""
from __future__ import annotations

import asyncio
import random

import aiohttp

from livevoice.core.models import LiveEvent, User
from livevoice.platforms.base import PlatformClient


IRC_URL = "wss://irc-ws.chat.twitch.tv:443"

_TAG_ESCAPES = {"\\s": " ", "\\:": ";", "\\\\": "\\", "\\r": "\r", "\\n": "\n"}


def _unescape(value: str) -> str:
    for source, target in _TAG_ESCAPES.items():
        value = value.replace(source, target)
    return value


def parse_irc(line: str) -> dict:
    """Separa una línea IRCv3 en tags, prefijo, comando, parámetros y texto."""
    tags: dict[str, str] = {}
    if line.startswith("@"):
        raw_tags, line = line[1:].split(" ", 1)
        for item in raw_tags.split(";"):
            key, _, value = item.partition("=")
            tags[key] = _unescape(value)
    prefix = ""
    if line.startswith(":"):
        prefix, line = line[1:].split(" ", 1)
    trailing = ""
    if " :" in line:
        line, trailing = line.split(" :", 1)
    parts = line.split()
    return {
        "tags": tags,
        "prefix": prefix,
        "command": parts[0] if parts else "",
        "params": parts[1:],
        "text": trailing,
    }


class TwitchPlatform(PlatformClient):
    name = "twitch"
    label = "Twitch"

    def __init__(self, config):
        super().__init__(config)
        self._session: aiohttp.ClientSession | None = None

    @staticmethod
    def normalize_channel(channel: str) -> str:
        return PlatformClient.normalize_channel(channel).lower()

    def _user(self, tags: dict, prefix: str = "") -> User:
        badges = tags.get("badges", "")
        login = tags.get("login") or prefix.split("!", 1)[0]
        return User(
            platform=self.name,
            id=tags.get("user-id", ""),
            username=login,
            display_name=tags.get("display-name") or login,
            color=tags.get("color", ""),
            is_moderator=tags.get("mod") == "1" or "broadcaster/" in badges,
            is_subscriber=tags.get("subscriber") == "1" or "founder/" in badges,
            is_broadcaster="broadcaster/" in badges,
            is_vip="vip/" in badges,
        )

    async def session(self):
        self._session = aiohttp.ClientSession()
        async with self._session.ws_connect(IRC_URL, heartbeat=60) as ws:
            await ws.send_str("CAP REQ :twitch.tv/tags twitch.tv/commands")
            await ws.send_str("PASS SCHMOOPIIE")
            await ws.send_str(f"NICK justinfan{random.randint(10000, 99999)}")
            await ws.send_str(f"JOIN #{self.channel}")

            async for message in ws:
                if message.type != aiohttp.WSMsgType.TEXT:
                    if message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
                    continue
                for line in message.data.split("\r\n"):
                    if line:
                        await self._handle(ws, line)

    async def _handle(self, ws, line: str):
        if line.startswith("PING"):
            await ws.send_str("PONG :tmi.twitch.tv")
            return
        msg = parse_irc(line)
        command, tags = msg["command"], msg["tags"]

        if command == "ROOMSTATE" or (command == "JOIN" and msg["prefix"].startswith("justinfan")):
            if self.status != "connected":
                self.set_status("connected", f"Conectado al chat de #{self.channel}")
        elif command == "NOTICE" and "msg_channel_suspended" in tags.get("msg-id", ""):
            self.set_status("error", "Este canal está suspendido.")
        elif command == "RECONNECT":
            await ws.close()
        elif command == "PRIVMSG":
            user = self._user(tags, msg["prefix"])
            text = msg["text"]
            if text.startswith("\x01ACTION "):
                text = text[8:].rstrip("\x01")
            bits = int(tags.get("bits", 0) or 0)
            if bits:
                await self.publish(LiveEvent(kind="bits", platform=self.name, user=user, text=text, amount=bits, value=bits))
            await self.publish(LiveEvent(kind="chat", platform=self.name, user=user, text=text))
        elif command == "USERNOTICE":
            await self._usernotice(tags, msg["text"])

    async def _usernotice(self, tags: dict, text: str):
        kind = tags.get("msg-id", "")
        user = self._user(tags)
        if kind in ("sub", "resub", "primepaidupgrade", "giftpaidupgrade"):
            months = int(tags.get("msg-param-cumulative-months", 1) or 1)
            await self.publish(LiveEvent(kind="sub", platform=self.name, user=user, text=text, amount=months))
        elif kind == "subgift":
            await self.publish(LiveEvent(kind="sub", platform=self.name, user=user, gift="sub", amount=1, text=text))
        elif kind == "submysterygift":
            count = int(tags.get("msg-param-mass-gift-count", 1) or 1)
            await self.publish(LiveEvent(kind="gift", platform=self.name, user=user, gift="subs", amount=count, value=count * 500))
        elif kind == "raid":
            viewers = int(tags.get("msg-param-viewerCount", 0) or 0)
            await self.publish(LiveEvent(kind="raid", platform=self.name, user=user, amount=viewers))

    async def close(self):
        session, self._session = self._session, None
        if session and not session.closed:
            await session.close()
