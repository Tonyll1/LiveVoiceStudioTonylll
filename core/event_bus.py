from collections import defaultdict
from dataclasses import dataclass, field
from itertools import count
from threading import RLock
from typing import Callable

from core.events import Priority
from core.logger import logger


@dataclass(order=True)
class _Listener:
    sort_index: tuple[int, int] = field(init=False, repr=False)
    priority: int
    order: int
    callback: Callable = field(compare=False)
    once: bool = field(default=False, compare=False)

    def __post_init__(self):
        self.sort_index = (-self.priority, self.order)


class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)
        self._lock = RLock()
        self._counter = count()

    def subscribe(
        self,
        event_name: str,
        callback: Callable,
        priority: Priority | int = Priority.NORMAL,
        once: bool = False,
        unique: bool = True
    ):
        priority_value = int(priority.value if hasattr(priority, "value") else priority)

        with self._lock:
            if unique:
                for listener in self._listeners[event_name]:
                    if listener.callback == callback:
                        return

            listener = _Listener(
                priority=priority_value,
                order=next(self._counter),
                callback=callback,
                once=once
            )

            self._listeners[event_name].append(listener)
            self._listeners[event_name].sort()

    def unsubscribe(self, event_name: str, callback: Callable):
        with self._lock:
            self._listeners[event_name] = [
                listener
                for listener in self._listeners[event_name]
                if listener.callback != callback
            ]

    def emit(self, event_name: str, *args, **kwargs):
        with self._lock:
            listeners = list(self._listeners[event_name])

        callbacks_to_remove = []

        for listener in listeners:
            try:
                listener.callback(*args, **kwargs)
            except Exception as error:
                logger.exception(
                    "Error en evento %s: %s",
                    event_name,
                    error
                )

            if listener.once:
                callbacks_to_remove.append(listener.callback)

        for callback in callbacks_to_remove:
            self.unsubscribe(event_name, callback)


event_bus = EventBus()