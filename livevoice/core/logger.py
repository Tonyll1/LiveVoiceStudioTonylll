import logging
from logging.handlers import RotatingFileHandler

from livevoice.core.paths import data_path, ensure_runtime_directories


ensure_runtime_directories()

_handler = RotatingFileHandler(
    data_path("logs", "livevoice.log"),
    maxBytes=2_000_000,
    backupCount=3,
    encoding="utf-8",
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
)

root = logging.getLogger()
root.setLevel(logging.INFO)
root.addHandler(_handler)

# Las librerías de red registran cada petición; solo nos interesan sus avisos.
for noisy in ("httpx", "httpcore", "websockets", "aiohttp.access", "TikTokLive"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("LiveVoiceStudio")
