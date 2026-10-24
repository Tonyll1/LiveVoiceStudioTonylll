"""Base común: reconexión automática, espera a que empiece el directo y estados."""
from __future__ import annotations

import asyncio
import random

from livevoice.core.bus import bus
from livevoice.core.logger import logger
from livevoice.core.models import LiveEvent


class ChannelOffline(Exception):
    """El canal existe pero no está en directo: se reintenta cada cierto tiempo."""


class ChannelNotFound(Exception):
    """El canal no existe: no tiene sentido reintentar."""


class PlatformClient:
    name = "base"
    label = "Plataforma"
    OFFLINE_RETRY_SECONDS = 30

    def __init__(self, config):
        self.config = config
        self.channel = ""
        self.status = "offline"
        self.message = ""
        self.viewers = 0
        self._task: asyncio.Task | None = None

    # ── Control ────────────────────────────────────────────────────

    async def connect(self, channel: str):
        await self.disconnect()
        self.channel = self.normalize_channel(channel)
        if not self.channel:
            self.set_status("error", "Escribe un canal válido.")
            return
        self._task = asyncio.create_task(self._run_forever(), name=f"{self.name}-client")

    async def disconnect(self):
        task, self._task = self._task, None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        await self.close()
        if self.status != "offline":
            self.set_status("offline", "Desconectado")

    @property
    def active(self) -> bool:
        return self._task is not None and not self._task.done()

    @staticmethod
    def normalize_channel(channel: str) -> str:
        channel = (channel or "").strip()
        for prefix in ("https://", "http://", "www."):
            if channel.lower().startswith(prefix):
                channel = channel[len(prefix):]
        if "/" in channel:
            parts = [part for part in channel.split("/") if part]
            channel = parts[1] if len(parts) > 1 else parts[0]
        return channel.lstrip("@").strip()

    # ── Para subclases ─────────────────────────────────────────────

    async def session(self):
        """Conecta y procesa eventos hasta que la conexión termine."""
        raise NotImplementedError

    async def close(self):
        pass

    # ── Utilidades ─────────────────────────────────────────────────

    def set_status(self, status: str, message: str = ""):
        self.status, self.message = status, message
        bus.emit_nowait("platform.status", self.name, self.info())
        bus.emit_nowait("ws", "platform.status", self.info())

    def info(self) -> dict:
        return {
            "platform": self.name,
            "label": self.label,
            "channel": self.channel,
            "status": self.status,
            "message": self.message,
            "viewers": self.viewers,
        }

    async def publish(self, event: LiveEvent):
        await bus.emit("live.event", event)

    def set_viewers(self, viewers: int):
        if viewers != self.viewers:
            self.viewers = viewers
            bus.emit_nowait("ws", "platform.status", self.info())

    async def _run_forever(self):
        attempt = 0
        while True:
            try:
                self.set_status("connecting", f"Conectando con {self.channel}...")
                await self.session()
                attempt = 0
                self.set_status("reconnecting", "Conexión cerrada, reconectando...")
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except ChannelNotFound as error:
                self.set_status("error", str(error) or "Canal no encontrado.")
                return
            except ChannelOffline as error:
                attempt = 0
                self.set_status(
                    "waiting",
                    str(error) or f"{self.channel} no está en directo. Reintentando cada {self.OFFLINE_RETRY_SECONDS}s...",
                )
                await asyncio.sleep(self.OFFLINE_RETRY_SECONDS)
            except Exception as error:
                attempt += 1
                delay = min(60, 2 ** min(attempt, 6)) + random.uniform(0, 2)
                logger.warning("%s: error de conexión (%s). Reintento en %.0fs", self.name, error, delay)
                self.set_status("reconnecting", f"Error: {str(error)[:120]}. Reintento en {delay:.0f}s")
                await asyncio.sleep(delay)
            finally:
                try:
                    await self.close()
                except Exception:
                    pass
