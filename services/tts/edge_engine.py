import asyncio

import edge_tts

from services.audio.cache import AudioCache


class EdgeEngine:
    def __init__(self, cache: AudioCache):
        self.cache = cache
        self.loop = asyncio.new_event_loop()

    async def _synthesize(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str
    ):
        filename = self.cache.filename(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume
        )

        if filename.exists():
            return filename

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume
        )

        await communicate.save(str(filename))

        return filename

    def synthesize(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        volume: str = "+0%"
    ):
        return self.loop.run_until_complete(
            self._synthesize(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume
            )
        )