"""Bus de eventos asíncrono.

Todo el backend corre en un único event loop de asyncio. Los hilos auxiliares
(atajos de teclado, reproducción de audio) publican con `emit_threadsafe`.
"""
from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable

from livevoice.core.logger import logger


class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[tuple[int, Callable]]] = defaultdict(list)
        self.loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def on(self, event: str, callback: Callable, priority: int = 0):
        listeners = self._listeners[event]
        if any(existing is callback for _, existing in listeners):
            return
        listeners.append((priority, callback))
        listeners.sort(key=lambda item: -item[0])

    def off(self, event: str, callback: Callable):
        self._listeners[event] = [item for item in self._listeners[event] if item[1] is not callback]

    async def emit(self, event: str, *args: Any):
        """Llama a los listeners del evento y luego a los comodín '*' (que reciben el nombre)."""
        calls = [(callback, args) for _, callback in self._listeners[event]]
        calls += [(callback, (event, *args)) for _, callback in self._listeners["*"]]
        for callback, call_args in calls:
            try:
                result = callback(*call_args)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Error procesando el evento %s en %s", event, getattr(callback, "__qualname__", callback))

    def emit_nowait(self, event: str, *args: Any):
        """Publica desde el propio loop sin esperar a los listeners."""
        if self.loop is None:
            return
        self.loop.create_task(self.emit(event, *args))

    def emit_threadsafe(self, event: str, *args: Any):
        if self.loop is None or self.loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self.emit(event, *args), self.loop)


bus = EventBus()
