import logging

from core.paths import data_path, ensure_runtime_directories


ensure_runtime_directories()

logging.basicConfig(
    filename=data_path("logs", "livevoice.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    encoding="utf-8",
)

logger = logging.getLogger("LiveVoiceStudio")
