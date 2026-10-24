"""Chat de Kick vía Pusher. La clave de Pusher se resuelve en cada conexión porque Kick la rota."""
from __future__ import annotations

import asyncio
import json
import uuid

import aiohttp

from livevoice.core.logger import logger
from livevoice.core.models import LiveEvent, User
from livevoice.platforms.base import ChannelNotFound, PlatformClient


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
}
DEFAULT_PUSHER = ("34bf7a0ff419a2a775b9", "us2")


class KickPlatform(PlatformClient):
    name = "kick"
    label = "Kick"

    def __init__(self, config):
        super().__init__(config)
        self._session: aiohttp.ClientSession | None = None

    @staticmethod
    def normalize_channel(channel: str) -> str:
        return PlatformClient.normalize_channel(channel).lower().replace("_", "-")

    async def _pusher_credentials(self) -> tuple[str, str]:
        body = {
            "client": {"id": str(uuid.uuid4()), "type": "web"},
            "capabilities": {"accepted_providers": [{"provider": "pusher"}]},
        }
        try:
            async with self._session.post(
                "https://web.kick.com/api/v1/realtime/connection", json=body, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                data = await response.json(content_type=None)
            for connection in data.get("data", {}).get("connections", []):
                if connection.get("provider") == "pusher":
                    credentials = connection.get("credentials", {})
                    return credentials["app_key"], credentials.get("cluster", "us2")
        except Exception as error:
            logger.warning("Kick: no se pudo negociar la clave de Pusher, se usa la conocida: %s", error)
        return DEFAULT_PUSHER

    async def _channel_info(self) -> dict:
        url = f"https://kick.com/api/v2/channels/{self.channel}"
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status == 404:
                raise ChannelNotFound(f"El canal {self.channel} no existe en Kick.")
            if response.status != 200:
                raise ConnectionError(f"Kick respondió {response.status} al buscar el canal")
            return await response.json(content_type=None)

    async def session(self):
        self._session = aiohttp.ClientSession(headers=HEADERS)
        info = await self._channel_info()
        chatroom_id = info.get("chatroom", {}).get("id")
        channel_id = info.get("id")
        if not chatroom_id:
            raise ChannelNotFound("No se encontró el chat de este canal.")
        livestream = info.get("livestream") or {}
        self.set_viewers(int(livestream.get("viewer_count", 0) or 0))

        key, cluster = await self._pusher_credentials()
        url = f"wss://ws-{cluster}.pusher.com/app/{key}?protocol=7&client=js&version=8.4.0&flash=false"
        async with self._session.ws_connect(url, heartbeat=100) as ws:
            for channel in (f"chatrooms.{chatroom_id}.v2", f"chatrooms.{chatroom_id}", f"channel.{channel_id}"):
                await ws.send_str(json.dumps({"event": "pusher:subscribe", "data": {"auth": "", "channel": channel}}))

            async for message in ws:
                if message.type != aiohttp.WSMsgType.TEXT:
                    if message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
                    continue
                await self._handle(ws, json.loads(message.data))

    def _user(self, sender: dict) -> User:
        badges = {badge.get("type") for badge in sender.get("identity", {}).get("badges", [])}
        username = sender.get("slug") or sender.get("username", "")
        return User(
            platform=self.name,
            id=str(sender.get("id", "")),
            username=username,
            display_name=sender.get("username", username),
            color=sender.get("identity", {}).get("color", ""),
            is_moderator=bool(badges & {"moderator", "broadcaster"}),
            is_subscriber=bool(badges & {"subscriber", "founder", "og"}),
            is_broadcaster="broadcaster" in badges,
            is_vip="vip" in badges,
        )

    async def _handle(self, ws, payload: dict):
        event = payload.get("event", "")
        if event == "pusher:ping":
            await ws.send_str(json.dumps({"event": "pusher:pong", "data": {}}))
            return
        if event == "pusher:error":
            data = payload.get("data") or {}
            raise ConnectionError(f"Pusher: {data.get('message', data)}")
        if event == "pusher_internal:subscription_succeeded":
            if self.status != "connected":
                self.set_status("connected", f"Conectado al chat de {self.channel}")
            return

        raw = payload.get("data")
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        name = event.split("\\")[-1]

        if name == "ChatMessageEvent":
            await self.publish(LiveEvent(
                kind="chat", platform=self.name, user=self._user(data.get("sender", {})), text=data.get("content", "")
            ))
        elif name in ("SubscriptionEvent", "ChannelSubscriptionEvent"):
            user = User(platform=self.name, username=data.get("username", ""), display_name=data.get("username", ""))
            await self.publish(LiveEvent(kind="sub", platform=self.name, user=user, gift="Sub", amount=int(data.get("months", 1) or 1)))
        elif name == "GiftedSubscriptionsEvent":
            gifter = data.get("gifted_by", "")
            user = User(platform=self.name, username=gifter, display_name=gifter)
            count = len(data.get("gifted_usernames", [])) or 1
            await self.publish(LiveEvent(kind="gift", platform=self.name, user=user, gift="Subs regaladas", amount=count, value=count * 500))
        elif name == "StreamHostEvent":
            host = data.get("host_username", "")
            user = User(platform=self.name, username=host, display_name=host)
            await self.publish(LiveEvent(kind="raid", platform=self.name, user=user, amount=int(data.get("number_viewers", 0) or 0)))
        elif name == "KicksGifted" or name == "KicksGiftedEvent":
            sender = data.get("sender", {})
            gift = data.get("gift", {})
            user = User(platform=self.name, username=sender.get("username", ""), display_name=sender.get("username", ""))
            amount = int(gift.get("amount", 1) or 1)
            await self.publish(LiveEvent(kind="gift", platform=self.name, user=user, gift=gift.get("name", "Kicks"), amount=1, value=amount))
        elif name == "StopStreamBroadcast":
            raise ConnectionResetError("El directo terminó")

    async def close(self):
        session, self._session = self._session, None
        if session and not session.closed:
            await session.close()
            await asyncio.sleep(0)
