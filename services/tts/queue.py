from itertools import count
from queue import PriorityQueue

from core.events import Priority


class TTSQueue:
    def __init__(self):
        self._queue = PriorityQueue(maxsize=500)
        self._counter = count()

    def add(
        self,
        text: str,
        priority: Priority | int = Priority.NORMAL
    ):
        priority_value = int(priority.value if hasattr(priority, "value") else priority)

        self._queue.put(
            (
                -priority_value,
                next(self._counter),
                text
            )
        )

    def next(self):
        priority, _, text = self._queue.get()
        return text, -priority

    def clear(self):
        while not self._queue.empty():
            self._queue.get()

    def size(self):
        return self._queue.qsize()