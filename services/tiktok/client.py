import asyncio
import logging
import threading

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    ConnectEvent,
    DisconnectEvent,
    CommentEvent,
    FollowEvent,
    GiftEvent,
    LikeEvent,
)

from core.constants import (
    COMMENT_EVENT,
    FOLLOW_EVENT,
    GIFT_EVENT,
    LIKE_EVENT,
    CONNECT_EVENT,
    DISCONNECT_EVENT,
    ERROR_EVENT,
    STATUS_EVENT,
)
from core.event_bus import event_bus
from core.logger import logger

from models.comment import Comment
from models.follow import Follow
from models.gift import Gift
from models.like import Like
from models.user import User

from services.tiktok.filters import MessageFilter


class TikTokClient:
    def __init__(self, config):
        self.client = None
        self.username = None
        self.connected = False
        self.thread = None
        self.loop = None

        self.config = config
        self.filter = MessageFilter(config)

    def connect(self, username: str):
        username = username.strip().replace("@", "")

        if not username:
            event_bus.emit(ERROR_EVENT, "Escribe un usuario válido.")
            return

        if self.thread and self.thread.is_alive():
            event_bus.emit(
                STATUS_EVENT,
                "Ya hay un intento de conexión activo."
            )
            return

        self.username = username

        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="TikTokLiveThread",
        )
        self.thread.start()

    def _run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._start())
        except Exception as error:
            logger.exception("Error general en TikTokClient: %s", error)
            event_bus.emit(ERROR_EVENT, str(error))
        finally:
            if self.loop is not None:
                self.loop.close()
            self.loop = None

    def disconnect(self):
        if self.client is None or self.loop is None or not self.loop.is_running():
            return
        try:
            future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            future.result(timeout=5)
        except Exception as error:
            logger.warning("No se pudo desconectar TikTok limpiamente: %s", error)

    async def _start(self):
        self.client = TikTokLiveClient(
            unique_id=self.username
        )

        # Activa información útil en la terminal
        self.client.logger.setLevel(logging.INFO)

        self._register_events()

        try:
            event_bus.emit(
                STATUS_EVENT,
                f"Comprobando si @{self.username} está en vivo..."
            )

            try:
                is_live = await asyncio.wait_for(
                    self.client.is_live(),
                    timeout=20
                )
            except asyncio.TimeoutError:
                event_bus.emit(
                    ERROR_EVENT,
                    "TikTok tardó demasiado en responder."
                )
                return

            if not is_live:
                event_bus.emit(
                    ERROR_EVENT,
                    f"@{self.username} no está transmitiendo en este momento."
                )
                return

            event_bus.emit(
                STATUS_EVENT,
                f"Live encontrado. Conectando con @{self.username}..."
            )

            # En 6.6.5 start() devuelve una Task.
            connection_task = await asyncio.wait_for(
                self.client.start(),
                timeout=30
            )

            # Mantiene vivo el loop hasta que termine el LIVE o se desconecte.
            await connection_task

        except asyncio.TimeoutError:
            event_bus.emit(
                ERROR_EVENT,
                "No se pudo completar la conexión en 30 segundos."
            )

        except Exception as error:
            logger.exception(
                "Error conectando con @%s: %s",
                self.username,
                error
            )
            event_bus.emit(ERROR_EVENT, str(error))

    def _register_events(self):
        @self.client.on(ConnectEvent)
        async def on_connect(event):
            self.connected = True

            logger.info(
                "Conectado a TikTok LIVE: @%s | Room ID: %s",
                self.username,
                self.client.room_id,
            )

            event_bus.emit(CONNECT_EVENT, "tiktok", self.username)

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event):
            self.connected = False
            logger.warning(
                "Desconectado de TikTok LIVE: @%s",
                self.username
            )
            event_bus.emit(DISCONNECT_EVENT, "tiktok")

        @self.client.on(CommentEvent)
        async def on_comment(event):
            user = self._build_user(event.user)
            original_text = event.comment.strip()

            show_message, read_tts, processed_text = self.filter.process(
                user.id or user.username,
                original_text
            )

            if not show_message:
                return

            comment = Comment(
                user=user,
                text=processed_text
            )

            event_bus.emit(
                COMMENT_EVENT,
                comment,
                read_tts
            )

        @self.client.on(FollowEvent)
        async def on_follow(event):
            event_bus.emit(
                FOLLOW_EVENT,
                Follow(
                    user=self._build_user(event.user)
                )
            )

        @self.client.on(GiftEvent)
        async def on_gift(event):
            if event.gift is None:
                return

            # Evita leer cada paso intermedio de regalos en racha.
            if getattr(event, "streaking", False):
                return

            event_bus.emit(
                GIFT_EVENT,
                Gift(
                    user=self._build_user(event.user),
                    gift_name=event.gift.name,
                    amount=getattr(event, "repeat_count", 1),
                )
            )

        @self.client.on(LikeEvent)
        async def on_like(event):
            event_bus.emit(
                LIKE_EVENT,
                Like(
                    user=self._build_user(event.user),
                    count=getattr(event, "count", 1),
                )
            )

    def _build_user(self, raw_user) -> User:
        return User(
            id=str(
                getattr(raw_user, "user_id", "")
                or getattr(raw_user, "id", "")
                or ""
            ),
            username=(
                getattr(raw_user, "unique_id", "")
                or getattr(raw_user, "username", "")
                or ""
            ),
            nickname=(
                getattr(raw_user, "nickname", "")
                or getattr(raw_user, "unique_id", "")
                or "Usuario"
            ),
            photo=None,
        )