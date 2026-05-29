import time

from app.core.exceptions import CapacityError, KeyNotFound, TypeMismatch
from app.core.models import Entry, Value


class MemoryStore:
    def __init__(self, initial_capacity: int, max_keys: int, default_ttl: int = 0) -> None:
        self._max_keys = max_keys
        self._default_ttl = default_ttl
        self._slots: list[Entry | None] = [None] * initial_capacity
        # Stack of free slot indices; pop() gives the next available slot
        self._free: list[int] = list(range(initial_capacity - 1, -1, -1))
        self._key_index: dict[str, int] = {}

    def get(self, key: str) -> Entry:
        if key not in self._key_index:
            raise KeyNotFound(key)
        entry = self._slots[self._key_index[key]]
        assert entry is not None
        return entry

    def set(self, key: str, value: Value, value_type: str, ttl: int | None) -> None:
        if key in self._key_index:
            slot = self._key_index[key]
            existing = self._slots[slot]
            assert existing is not None
            if existing.value_type != value_type:
                raise TypeMismatch(key, value_type, existing.value_type)
            self._slots[slot] = Entry(value=value, value_type=value_type, expires_at=existing.expires_at)
            return

        if len(self._key_index) >= self._max_keys:
            raise CapacityError("Store is full")
        if not self._free:
            raise CapacityError("No free slots")

        slot = self._free.pop()
        self._slots[slot] = Entry(value=value, value_type=value_type)
        self._key_index[key] = slot

    def delete(self, key: str) -> None:
        if key not in self._key_index:
            raise KeyNotFound(key)
        slot = self._key_index.pop(key)
        self._slots[slot] = None
        self._free.append(slot)

    def exists(self, key: str) -> bool:
        return key in self._key_index

    def update_value(self, key: str, value: Value) -> None:
        if key not in self._key_index:
            raise KeyNotFound(key)
        slot = self._key_index[key]
        existing = self._slots[slot]
        assert existing is not None
        self._slots[slot] = Entry(
            value=value,
            value_type=existing.value_type,
            expires_at=existing.expires_at,
        )

    def expire(self, key: str, ttl: int) -> None:
        if key not in self._key_index:
            raise KeyNotFound(key)
        slot = self._key_index[key]
        existing = self._slots[slot]
        assert existing is not None
        self._slots[slot] = Entry(
            value=existing.value,
            value_type=existing.value_type,
            expires_at=time.time() + ttl,
        )

    def keys(self) -> list[str]:
        return list(self._key_index.keys())

    def flush(self) -> None:
        size = len(self._slots)
        self._slots = [None] * size
        self._free = list(range(size - 1, -1, -1))
        self._key_index = {}
