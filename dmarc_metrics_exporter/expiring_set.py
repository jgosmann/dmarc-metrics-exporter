import time
from collections import deque
from collections.abc import Container
from typing import Callable, Deque, Generic, Set, Tuple, TypeVar

T = TypeVar("T")


class ExpiringSet(Generic[T], Container):
    _items: Set[T]
    _expiry_queue: Deque[Tuple[float, T]]

    def __init__(self, ttl: float, time_fn: Callable[[], float] = time.time):
        self.ttl = ttl
        self._time = time_fn
        self._items = set()
        self._expiry_queue = deque()

    def add(self, item: T):
        self._expire()
        self._items.add(item)
        self._expiry_queue.append((self._time(), item))

    def __contains__(self, item: object) -> bool:
        self._expire()
        return item in self._items

    def _expire(self):
        while (
            len(self._expiry_queue) > 0
            and self._time() - self._expiry_queue[0][0] >= self.ttl
        ):
            _, item = self._expiry_queue.popleft()
            self._items.remove(item)
