from enum import IntEnum


class Priority(IntEnum):
    LOW = 0
    NORMAL = 10
    HIGH = 50
    CRITICAL = 100