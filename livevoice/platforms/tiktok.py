from __future__ import annotations

import asyncio

from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import AgeRestrictedError, UserNotFoundError, UserOfflineError
from TikTokLive.client.web.web_settings import WebDefaults
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    DisconnectEvent,
    FollowEvent,
    GiftEvent,
    JoinEvent,
    LikeEvent,
    LiveEndEvent,
    RoomUserSeqEvent,
    ShareEvent,
    SubscribeEvent,
)

from livevoice.core.models import LiveEvent, User
from livevoice.platforms.base import ChannelNotFound, ChannelOffline, PlatformClient


def _first_url(image) -> str:
    urls = getattr(image, "m_urls", None) or []
    return urls[0] if urls else ""


class TikTokPlatform(PlatformClient):
    name = "tiktok"
    label = "TikTok"

    def __init__(self, config):
        super().__init__(config)
        self.client: TikTokLiveClient | None = None
        self._ended: asyncio.Event | None = None

    def _user(self, raw, identity=None) -> User:
        return User(
            platform=self.name,
            id=str(getattr(raw, "id", "") or ""),
            username=getattr(raw, "unique_id", "") or "",
            display_name=getattr(raw, "nickname", "") or getattr(raw, "unique_id", "") or "",
            avatar=_first_url(getattr(raw, "avatar_thumb", None)),
            is_moderator=bool(getattr(identity, "is_moderator_of_anchor", False) or getattr(raw, "is_moderator", False)),
            is_subscriber=bool(getattr(identity, "is_subscriber_of_anchor", False)),
            is_follower=bool(getattr(identity, "is_follower_of_anchor", False)),
            is_broadcaster=bool(getattr(identity, "is_anchor", False)),
            gifter_level=int(getattr(raw, "gifter_level", 0) or 0) if hasattr(raw, "gifter_level") else 0,
        )

    async def session(self):
        api_key = self.config.get("platforms.tiktok.sign_api_key", "")
        if api_key:
            WebDefaults.tiktok_sign_api_key = api_key

        client = TikTokLiveClient(unique_id=self.channel)
        self.client = client
        self._ended = asyncio.Event()
        self._register(client)

        try:
            live = await asyncio.wait_for(client.is_live(), timeout=20)
        except UserNotFoundError as error:
            raise ChannelNotFound(f"El usuario @{self.channel} no existe en TikTok.") from error
        if not live:
            raise ChannelOffline(f"@{self.channel} no está en directo. Esperando a que empiece...")

        try:
            task = await asyncio.wait_for(client.start(fetch_room_info=False), timeout=40)
        except UserOfflineError as error:
            raise ChannelOffline(f"@{self.channel} no está en directo.") from error
        except AgeRestrictedError as error:
            raise ChannelNotFound("El directo tiene restricción de edad; TikTok no deja leerlo sin sesión.") from error

        ended_wait = asyncio.create_task(self._ended.wait())
        done, _ = await asyncio.wait({task, ended_wait}, return_when=asyncio.FIRST_COMPLETED)
        ended_wait.cancel()
        if task in done and task.exception():
            raise task.exception()

    async def close(self):
        client, self.client = self.client, None
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass

    def _register(self, client: TikTokLiveClient):
        @client.on(ConnectEvent)
        async def on_connect(_event):
            self.set_status("connected", f"Conectado a @{self.channel}")

        @client.on(DisconnectEvent)
        async def on_disconnect(_event):
            if self._ended:
                self._ended.set()

        @client.on(LiveEndEvent)
        async def on_end(_event):
            self.set_status("waiting", "El directo terminó.")
            if self._ended:
                self._ended.set()

        @client.on(RoomUserSeqEvent)
        async def on_viewers(event):
            self.set_viewers(int(getattr(event, "m_total", 0) or 0))

        @client.on(CommentEvent)
        async def on_comment(event):
            await self.publish(LiveEvent(
                kind="chat",
                platform=self.name,
                user=self._user(event.user, getattr(event, "user_identity", None)),
                text=(event.comment or "").strip(),
            ))

        @client.on(FollowEvent)
        async def on_follow(event):
            await self.publish(LiveEvent(kind="follow", platform=self.name, user=self._user(event.user)))

        @client.on(ShareEvent)
        async def on_share(event):
            await self.publish(LiveEvent(kind="share", platform=self.name, user=self._user(event.user)))

        @client.on(JoinEvent)
        async def on_join(event):
            await self.publish(LiveEvent(kind="join", platform=self.name, user=self._user(event.user)))

        @client.on(SubscribeEvent)
        async def on_sub(event):
            await self.publish(LiveEvent(kind="sub", platform=self.name, user=self._user(event.user), gift="Super fan"))

        @client.on(LikeEvent)
        async def on_like(event):
            await self.publish(LiveEvent(
                kind="like",
                platform=self.name,
                user=self._user(event.user),
                amount=int(getattr(event, "count", 1) or 1),
                value=int(getattr(event, "total", 0) or 0),
            ))

        @client.on(GiftEvent)
        async def on_gift(event):
            gift = event.gift
            if gift is None or event.streaking:
                return
            count = int(getattr(event, "repeat_count", 1) or 1)
            diamonds = int(getattr(gift, "diamond_count", 0) or 0)
            await self.publish(LiveEvent(
                kind="gift",
                platform=self.name,
                user=self._user(event.user),
                gift=gift.name or "regalo",
                amount=count,
                value=diamonds * count,
                image=_first_url(getattr(gift, "image", None)),
            ))
