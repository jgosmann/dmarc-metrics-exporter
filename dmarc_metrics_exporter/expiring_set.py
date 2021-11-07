import pickle
import time
from collections import deque
from collections.abc import Container
from pathlib import Path
from typing import Callable, Deque, Generic, Set, Tuple, TypeVar, Union

T = TypeVar("T")


class ExpiringSet(Generic[T], Container):
    __PICKLE_PROTOCOL = 4
    __VERSION = 0

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

    def persist(self, path: Union[Path, str]):
        self._expire()
        with open(path, "wb") as f:
            pickle.dump(
                {"version": self.__VERSION, "expiry_queue": self._expiry_queue},
                f,
                self.__PICKLE_PROTOCOL,
            )

    @classmethod
    def load(
        cls,
        path: Union[Path, str],
        ttl: float,
        time_fn: Callable[[], float] = time.time,
    ) -> "ExpiringSet[T]":
        # pylint: disable=protected-access
        reconstructed = ExpiringSet[T](ttl, time_fn)
        with open(path, "rb") as f:
            data = pickle.load(f)
            if data["version"] != cls.__VERSION:
                raise RuntimeError("Unsupported version.")
            reconstructed._expiry_queue.extend(
                (timestamp, item)
                for timestamp, item in data["expiry_queue"]
                if time_fn() - timestamp < ttl
            )
            reconstructed._items.update(item for _, item in reconstructed._expiry_queue)
        return reconstructed
