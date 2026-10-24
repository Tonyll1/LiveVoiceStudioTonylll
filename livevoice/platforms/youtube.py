"""Chat de YouTube Live leyendo la API interna del navegador (sin clave de API ni cuota)."""
from __future__ import annotations

import asyncio
import re

import aiohttp

from livevoice.core.models import LiveEvent, User
from livevoice.platforms.base import ChannelNotFound, ChannelOffline, PlatformClient


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|/live/)([\w-]{11})")


def _runs_text(message: dict) -> str:
    if "simpleText" in message:
        return message["simpleText"]
    parts = []
    for run in message.get("runs", []):
        if "text" in run:
            parts.append(run["text"])
        elif "emoji" in run:
            shortcuts = run["emoji"].get("shortcuts") or [""]
            parts.append(shortcuts[0] if run["emoji"].get("isCustomEmoji") else run["emoji"].get("emojiId", ""))
    return "".join(parts)


def _amount(text: str) -> int:
    digits = re.sub(r"[^\d.,]", "", text).replace(",", "")
    try:
        return int(float(digits or 0))
    except ValueError:
        return 0


class YouTubePlatform(PlatformClient):
    name = "youtube"
    label = "YouTube"

    def __init__(self, config):
        super().__init__(config)
        self._session: aiohttp.ClientSession | None = None

    @staticmethod
    def normalize_channel(channel: str) -> str:
        channel = (channel or "").strip()
        match = VIDEO_ID_RE.search(channel)
        if match:
            return match.group(1)
        if "youtube.com/" in channel:
            channel = channel.split("youtube.com/", 1)[1].split("?")[0].strip("/")
            channel = channel.split("/")[0] if channel.startswith("@") else channel
        return channel.strip()

    async def _get(self, url: str) -> str:
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
            if response.status == 404:
                raise ChannelNotFound("Canal o video de YouTube no encontrado.")
            return await response.text()

    async def _resolve_video(self) -> str:
        target = self.channel
        if re.fullmatch(r"[\w-]{11}", target) and not target.startswith("@"):
            return target
        if target.startswith("UC") and len(target) == 24:
            page = f"https://www.youtube.com/channel/{target}/live"
        else:
            handle = target if target.startswith("@") else f"@{target}"
            page = f"https://www.youtube.com/{handle}/live"
        html = await self._get(page)
        canonical = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})"', html)
        if not canonical:
            raise ChannelOffline(f"{target} no está en directo en YouTube. Esperando...")
        return canonical.group(1)

    async def session(self):
        self._session = aiohttp.ClientSession(headers=HEADERS, cookies={"CONSENT": "YES+1"})
        video_id = await self._resolve_video()
        html = await self._get(f"https://www.youtube.com/live_chat?is_popout=1&v={video_id}")
        key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
        version = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html) or re.search(r'"clientVersion":"([^"]+)"', html)
        continuation = re.search(r'"continuation":"([^"]+)"', html)
        if not (key and version and continuation):
            raise ChannelOffline("Este video no tiene chat en vivo activo.")

        self.set_status("connected", f"Conectado al chat de YouTube ({video_id})")
        token = continuation.group(1)
        url = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={key.group(1)}&prettyPrint=false"
        context = {"client": {"clientName": "WEB", "clientVersion": version.group(1), "hl": "es"}}

        while True:
            async with self._session.post(url, json={"context": context, "continuation": token},
                                          timeout=aiohttp.ClientTimeout(total=20)) as response:
                if response.status != 200:
                    raise ConnectionError(f"YouTube respondió {response.status}")
                data = await response.json(content_type=None)
            chat = data.get("continuationContents", {}).get("liveChatContinuation")
            if not chat:
                raise ChannelOffline("El directo de YouTube terminó.")
            for action in chat.get("actions", []):
                item = action.get("addChatItemAction", {}).get("item")
                if item:
                    await self._handle(item)
            continuations = chat.get("continuations", [])
            if not continuations:
                raise ChannelOffline("El directo de YouTube terminó.")
            info = next(iter(continuations[0].values()))
            token = info.get("continuation", token)
            await asyncio.sleep(max(1.0, min(info.get("timeoutMs", 3000) / 1000, 8)))

    def _user(self, renderer: dict) -> User:
        badges = set()
        is_member = False
        for badge in renderer.get("authorBadges", []):
            badge_renderer = badge.get("liveChatAuthorBadgeRenderer", {})
            icon = badge_renderer.get("icon", {}).get("iconType")
            if icon:
                badges.add(icon)
            elif badge_renderer.get("customThumbnail"):
                is_member = True
        thumbs = renderer.get("authorPhoto", {}).get("thumbnails", [])
        name = renderer.get("authorName", {}).get("simpleText", "")
        return User(
            platform=self.name,
            id=renderer.get("authorExternalChannelId", ""),
            username=name.lstrip("@"),
            display_name=name.lstrip("@"),
            avatar=thumbs[-1]["url"] if thumbs else "",
            is_moderator=bool(badges & {"MODERATOR", "OWNER"}),
            is_broadcaster="OWNER" in badges,
            is_subscriber=is_member,
        )

    async def _handle(self, item: dict):
        if "liveChatTextMessageRenderer" in item:
            renderer = item["liveChatTextMessageRenderer"]
            await self.publish(LiveEvent(
                kind="chat", platform=self.name, user=self._user(renderer), text=_runs_text(renderer.get("message", {}))
            ))
        elif "liveChatPaidMessageRenderer" in item:
            renderer = item["liveChatPaidMessageRenderer"]
            amount_text = renderer.get("purchaseAmountText", {}).get("simpleText", "")
            text = _runs_text(renderer.get("message", {}))
            user = self._user(renderer)
            amount = max(1, _amount(amount_text))
            await self.publish(LiveEvent(
                kind="gift", platform=self.name, user=user, gift="Super Chat", amount=amount, value=amount, text=text,
            ))
            if text:
                await self.publish(LiveEvent(kind="chat", platform=self.name, user=user, text=text))
        elif "liveChatPaidStickerRenderer" in item:
            renderer = item["liveChatPaidStickerRenderer"]
            amount = max(1, _amount(renderer.get("purchaseAmountText", {}).get("simpleText", "")))
            await self.publish(LiveEvent(kind="gift", platform=self.name, user=self._user(renderer), gift="Super Sticker",
                                         amount=amount, value=amount))
        elif "liveChatMembershipItemRenderer" in item:
            renderer = item["liveChatMembershipItemRenderer"]
            await self.publish(LiveEvent(kind="sub", platform=self.name, user=self._user(renderer), gift="Miembro"))
        elif "liveChatSponsorshipsGiftPurchaseAnnouncementRenderer" in item:
            renderer = item["liveChatSponsorshipsGiftPurchaseAnnouncementRenderer"]
            header = renderer.get("header", {}).get("liveChatSponsorshipsHeaderRenderer", {})
            count = max(1, _amount(_runs_text(header.get("primaryText", {}))))
            await self.publish(LiveEvent(kind="gift", platform=self.name, user=self._user(header or renderer),
                                         gift="Membresías regaladas", amount=count, value=count * 5))

    async def close(self):
        session, self._session = self._session, None
        if session and not session.closed:
            await session.close()
