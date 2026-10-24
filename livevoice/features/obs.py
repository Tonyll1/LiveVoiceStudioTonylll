"""Clips con OBS (obs-websocket v5, incluido en OBS 28+).

Un "clip" guarda el Replay Buffer de OBS (los últimos N segundos) y además
anota una marca de tiempo en clips/marcas.csv para encontrar el momento en
la grabación o el VOD aunque OBS no esté conectado.
"""
from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import itertools
import json
import time
from datetime import datetime

import aiohttp

from livevoice.core.bus import bus
from livevoice.core.logger import logger
from livevoice.core.paths import data_path


class OBSClient:
    def __init__(self, config):
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ids = itertools.count(1)
        self._lock = asyncio.Lock()
        self.connected = False
        self.last_error = ""
        self._last_clip = 0.0
        self.clips_taken = 0

    async def _connect(self):
        settings = self.config.get("obs")
        await self.close()
        self._session = aiohttp.ClientSession()
        url = f"ws://{settings['host']}:{int(settings['port'])}"
        self._ws = await self._session.ws_connect(url, timeout=5, heartbeat=30)
        hello = json.loads((await self._ws.receive(timeout=5)).data)
        identify = {"rpcVersion": 1, "eventSubscriptions": 0}
        auth = hello.get("d", {}).get("authentication")
        if auth:
            password = settings.get("password", "")
            secret = base64.b64encode(hashlib.sha256((password + auth["salt"]).encode()).digest()).decode()
            identify["authentication"] = base64.b64encode(
                hashlib.sha256((secret + auth["challenge"]).encode()).digest()
            ).decode()
        await self._ws.send_str(json.dumps({"op": 1, "d": identify}))
        reply = await self._ws.receive(timeout=5)
        if reply.type != aiohttp.WSMsgType.TEXT or json.loads(reply.data).get("op") != 2:
            raise ConnectionError("OBS rechazó la conexión (¿contraseña incorrecta?)")
        self.connected = True
        self.last_error = ""

    async def request(self, request_type: str, data: dict | None = None) -> dict:
        async with self._lock:
            if not self.connected or self._ws is None or self._ws.closed:
                await self._connect()
            request_id = str(next(self._ids))
            await self._ws.send_str(json.dumps({
                "op": 6, "d": {"requestType": request_type, "requestId": request_id, "requestData": data or {}}
            }))
            while True:
                message = await self._ws.receive(timeout=10)
                if message.type != aiohttp.WSMsgType.TEXT:
                    self.connected = False
                    raise ConnectionError("Se perdió la conexión con OBS")
                payload = json.loads(message.data)
                if payload.get("op") == 7 and payload["d"].get("requestId") == request_id:
                    status = payload["d"].get("requestStatus", {})
                    if not status.get("result"):
                        raise RuntimeError(status.get("comment") or f"OBS error {status.get('code')}")
                    return payload["d"].get("responseData") or {}

    async def test(self) -> dict:
        try:
            version = await self.request("GetVersion")
            replay = await self.request("GetReplayBufferStatus")
            return {"ok": True, "obs_version": version.get("obsVersion"), "replay_buffer": replay.get("outputActive")}
        except Exception as error:
            self.connected = False
            self.last_error = str(error)
            return {"ok": False, "error": str(error) or "No se pudo conectar"}

    def _write_marker(self, reason: str, saved: bool):
        path = data_path("clips", "marcas.csv")
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if is_new:
                writer.writerow(["fecha", "hora", "motivo", "guardado_en_obs"])
            now = datetime.now()
            writer.writerow([now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), reason, "sí" if saved else "no"])

    async def clip(self, reason: str = "manual", *, respect_cooldown: bool = False) -> dict:
        cooldown = int(self.config.get("obs.clip_cooldown", 60) or 0)
        if respect_cooldown and time.monotonic() - self._last_clip < cooldown:
            return {"ok": False, "error": "cooldown"}
        self._last_clip = time.monotonic()

        saved, error = False, ""
        if self.config.get("obs.enabled"):
            try:
                status = await self.request("GetReplayBufferStatus")
                if not status.get("outputActive"):
                    await self.request("StartReplayBuffer")
                    error = "El Replay Buffer estaba apagado; se activó. El próximo clip sí se guardará."
                else:
                    await self.request("SaveReplayBuffer")
                    saved = True
                    try:
                        await self.request("CreateRecordChapter", {"chapterName": f"Clip: {reason}"[:60]})
                    except Exception:
                        pass
            except Exception as exc:
                self.connected = False
                error = str(exc) or "OBS no responde"
                logger.warning("No se pudo guardar el clip en OBS: %s", error)
        else:
            error = "OBS no está activado; solo se guardó la marca de tiempo."

        self._write_marker(reason, saved)
        self.clips_taken += 1
        result = {"ok": saved, "reason": reason, "error": error, "time": datetime.now().strftime("%H:%M:%S")}
        await bus.emit("ws", "clip", result)
        return result

    async def close(self):
        self.connected = False
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._ws = self._session = None
