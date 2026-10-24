"""Servidor local: panel de control, API y overlays para OBS (Browser Source)."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

from aiohttp import WSMsgType, web

from livevoice.audio.player import SUPPORTED_SOUND_EXTENSIONS, AudioPlayer
from livevoice.core.bus import bus
from livevoice.core.logger import logger
from livevoice.core.paths import data_path, resource_path


def _json(data, status: int = 200) -> web.Response:
    return web.json_response(data, status=status, dumps=lambda value: json.dumps(value, ensure_ascii=False, default=str))


class Server:
    def __init__(self, studio, host: str = "127.0.0.1", port: int = 8765):
        self.studio = studio
        self.host = host
        self.port = port
        self.clients: set[web.WebSocketResponse] = set()
        self.runner: web.AppRunner | None = None
        self.app = web.Application(client_max_size=50 * 1024 * 1024, middlewares=[self._no_cache])
        self._routes()
        bus.on("ws", self.broadcast)

    @web.middleware
    async def _no_cache(self, request, handler):
        response = await handler(request)
        if request.path.startswith(("/overlay", "/app", "/api")) or request.path == "/":
            response.headers["Cache-Control"] = "no-store"
        return response

    def _routes(self):
        web_root = resource_path("web")
        router = self.app.router
        router.add_get("/", lambda _request: web.HTTPFound("/app/"))
        router.add_get("/app/", self._file(web_root / "dashboard" / "index.html"))
        router.add_static("/app/", web_root / "dashboard")
        router.add_get("/overlay/{name}", self.overlay)
        router.add_static("/overlays/", web_root / "overlays")
        router.add_get("/ws", self.websocket)
        router.add_get("/api/state", self.get_state)
        router.add_get("/api/voices", self.get_voices)
        router.add_get("/api/audio-devices", self.get_audio_devices)
        router.add_get("/api/leaderboard", self.get_leaderboard)
        router.add_post("/api/config", self.post_config)
        router.add_post("/api/action/{name}", self.post_action)
        router.add_post("/api/upload-sound", self.upload_sound)
        router.add_get("/api/sounds", self.list_sounds)
        router.add_get("/sounds/{folder}/{name}", self.serve_sound)

    @staticmethod
    def _file(path: Path):
        async def handler(_request):
            return web.FileResponse(path)
        return handler

    # ── Páginas ────────────────────────────────────────────────────

    async def overlay(self, request: web.Request):
        name = request.match_info["name"].replace(".html", "")
        path = resource_path("web", "overlays", f"{name}.html")
        if not path.is_file():
            raise web.HTTPNotFound(text="Overlay no encontrado")
        return web.FileResponse(path)

    async def serve_sound(self, request: web.Request):
        folder = request.match_info["folder"]
        if folder not in ("commands", "alerts"):
            raise web.HTTPNotFound()
        path = data_path("sounds", folder, Path(request.match_info["name"]).name)
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    # ── WebSocket ──────────────────────────────────────────────────

    async def websocket(self, request: web.Request):
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        self.clients.add(ws)
        try:
            await ws.send_str(json.dumps({"type": "hello", "data": self._overlay_snapshot()}, ensure_ascii=False, default=str))
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    try:
                        payload = json.loads(message.data)
                        if payload.get("action"):
                            result = await self.studio.action(payload["action"], payload.get("data", {}))
                            await ws.send_str(json.dumps({"type": "result", "data": result}, default=str))
                    except Exception as error:
                        logger.warning("Mensaje WS inválido: %s", error)
                elif message.type == WSMsgType.ERROR:
                    break
        finally:
            self.clients.discard(ws)
        return ws

    def _overlay_snapshot(self) -> dict:
        return {
            "overlay": self.studio.config.get("overlay"),
            "goals": self.studio.goals.state(),
            "giveaway": self.studio.giveaway.state(),
            "poll": self.studio.poll.state(),
            "stats": self.studio.stats.to_dict(),
            "leaderboard": self.studio.viewers.top(10),
            "recent": [event for event in list(self.studio.stats.recent)[-20:] if event["kind"] == "chat"],
        }

    async def broadcast(self, kind: str, data):
        if not self.clients:
            return
        message = json.dumps({"type": kind, "data": data, "t": time.time()}, ensure_ascii=False, default=str)
        dead = []
        for client in list(self.clients):
            try:
                await client.send_str(message)
            except Exception:
                dead.append(client)
        for client in dead:
            self.clients.discard(client)

    # ── API ────────────────────────────────────────────────────────

    async def get_state(self, _request):
        return _json(self.studio.state())

    async def get_voices(self, _request):
        return _json(self.studio.catalog.to_list())

    async def get_audio_devices(self, _request):
        devices = await asyncio.to_thread(AudioPlayer.list_devices)
        return _json({"devices": devices, "current": self.studio.player.device})

    async def get_leaderboard(self, _request):
        return _json(self.studio.viewers.top(20))

    async def post_config(self, request: web.Request):
        patch = await request.json()
        if not isinstance(patch, dict):
            return _json({"ok": False, "error": "Formato inválido"}, 400)
        # Las listas (comandos, timers) se reemplazan al mezclar; estos diccionarios también,
        # para que borrar una entrada desde el panel funcione.
        replace = {
            "tts.user_voices": patch.get("tts", {}).pop("user_voices", None),
            "tts.replacements": patch.get("tts", {}).pop("replacements", None),
        }
        self.studio.config.update(patch)
        for path, value in replace.items():
            if isinstance(value, dict):
                self.studio.config.set(path, value)
        audio = patch.get("audio", {})
        if "tts_volume" in audio or "sfx_volume" in audio:
            self.studio.player.set_volumes(audio.get("tts_volume"), audio.get("sfx_volume"))
        if "hotkeys" in patch:
            self.studio.hotkeys.apply()
        if "overlay" in patch:
            await self.broadcast("overlay.config", self.studio.config.get("overlay"))
        if "goals" in patch:
            await self.studio.goals.publish()
        return _json({"ok": True, "config": self.studio.config.snapshot()})

    async def post_action(self, request: web.Request):
        try:
            data = await request.json() if request.can_read_body else {}
        except json.JSONDecodeError:
            data = {}
        try:
            result = await self.studio.action(request.match_info["name"], data)
        except ValueError as error:
            return _json({"ok": False, "error": str(error)}, 400)
        except Exception as error:
            logger.exception("Error en la acción %s", request.match_info["name"])
            return _json({"ok": False, "error": str(error)}, 500)
        return _json(result)

    async def upload_sound(self, request: web.Request):
        reader = await request.multipart()
        folder = "commands"
        saved = None
        async for part in reader:
            if part.name == "folder":
                value = (await part.text()).strip()
                folder = value if value in ("commands", "alerts") else "commands"
            elif part.name == "file" and part.filename:
                suffix = Path(part.filename).suffix.lower()
                if suffix not in SUPPORTED_SOUND_EXTENSIONS:
                    return _json({"ok": False, "error": "Formato no compatible. Usa MP3, WAV u OGG."}, 400)
                stem = "".join(char for char in Path(part.filename).stem if char.isalnum() or char in "-_ ")[:40] or "sonido"
                target = data_path("sounds", folder, f"{stem}-{uuid.uuid4().hex[:6]}{suffix}")
                with target.open("wb") as file:
                    while chunk := await part.read_chunk():
                        file.write(chunk)
                saved = target
        if saved is None:
            return _json({"ok": False, "error": "No se recibió ningún archivo."}, 400)
        return _json({"ok": True, "path": str(saved), "name": saved.name})

    async def list_sounds(self, _request):
        sounds = []
        for folder in ("commands", "alerts"):
            for path in sorted(data_path("sounds", folder, "x").parent.glob("*")):
                if path.suffix.lower() in SUPPORTED_SOUND_EXTENSIONS:
                    sounds.append({"folder": folder, "name": path.name, "path": str(path)})
        return _json(sounds)

    # ── Arranque ───────────────────────────────────────────────────

    async def start(self) -> int:
        self.runner = web.AppRunner(self.app, access_log=None)
        await self.runner.setup()
        for port in [self.port, *range(self.port + 1, self.port + 10)]:
            try:
                site = web.TCPSite(self.runner, self.host, port)
                await site.start()
                self.port = port
                return port
            except OSError:
                continue
        raise RuntimeError("No hay ningún puerto libre para el servidor local.")

    async def stop(self):
        for client in list(self.clients):
            await client.close()
        if self.runner:
            await self.runner.cleanup()
