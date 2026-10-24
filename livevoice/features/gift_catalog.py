"""Catálogo de regalos por plataforma para asignarles GIF, sonido y frase.

- TikTok: catálogo oficial completo (nombre, imagen y valor en diamantes), descargado y guardado en disco.
- Todas las plataformas: "regalos vistos", que se anotan solos cuando llegan en directo (así aparecen
  los Kicks de Kick o regalos nuevos de TikTok sin tener que escribir su nombre).
"""
from __future__ import annotations

import json
import threading
import time

from livevoice.core.logger import logger
from livevoice.core.models import LiveEvent
from livevoice.core.paths import data_path


class GiftCatalog:
    def __init__(self):
        self.tiktok_file = data_path("data", "gifts_tiktok.json")
        self.seen_file = data_path("data", "gifts_seen.json")
        self._lock = threading.Lock()
        self.seen: dict[str, dict[str, dict]] = self._read(self.seen_file, {})

    @staticmethod
    def _read(path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
        except Exception:
            return default

    def record(self, event: LiveEvent):
        """Anota un regalo recibido (para ofrecerlo luego en la lista de esa plataforma)."""
        # Los eventos simulados (Campo de pruebas) no cuentan como regalos reales.
        if event.kind != "gift" or not event.gift or event.user.id == "test":
            return
        with self._lock:
            gifts = self.seen.setdefault(event.platform, {})
            entry = gifts.setdefault(event.gift, {"name": event.gift, "image": "", "value": 0, "count": 0})
            entry["count"] += 1
            entry["image"] = event.image or entry["image"]
            entry["value"] = (event.value // max(1, event.amount)) if event.value else entry["value"]
            entry["last"] = time.time()
            self.seen_file.write_text(json.dumps(self.seen, ensure_ascii=False), encoding="utf-8")

    async def tiktok(self, refresh: bool = False) -> list[dict]:
        cached = self._read(self.tiktok_file, [])
        if cached and not refresh:
            return cached
        try:
            from TikTokLive import TikTokLiveClient

            client = TikTokLiveClient(unique_id="tiktok")
            data = await client.web.fetch_gift_list()
        except Exception as error:
            logger.warning("No se pudo descargar el catálogo de regalos de TikTok: %s", error)
            return cached

        by_name: dict[str, dict] = {}
        for gift in data.get("gifts", []):
            name = (gift.get("name") or "").strip()
            if not name:
                continue
            urls = (gift.get("image") or {}).get("url_list") or [""]
            item = {"name": name, "image": urls[0], "value": int(gift.get("diamond_count", 0) or 0)}
            # Algunos regalos se repiten con distinto id; nos quedamos con uno por nombre.
            by_name.setdefault(name, item)
        gifts = sorted(by_name.values(), key=lambda item: (item["value"], item["name"]))
        if gifts:
            self.tiktok_file.write_text(json.dumps(gifts, ensure_ascii=False), encoding="utf-8")
        return gifts or cached

    async def for_platform(self, platform: str, refresh: bool = False) -> list[dict]:
        seen = [{**item, "seen": True} for item in self.seen.get(platform, {}).values()]
        if platform != "tiktok":
            return sorted(seen, key=lambda item: -item.get("count", 0))
        seen_names = {item["name"] for item in seen}
        catalog = [item for item in await self.tiktok(refresh) if item["name"] not in seen_names]
        return sorted(seen, key=lambda item: -item.get("count", 0)) + catalog
