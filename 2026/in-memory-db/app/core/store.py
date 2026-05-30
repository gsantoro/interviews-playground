import time as _time

from app.core.exceptions import CapacityError, KeyNotFound, TypeMismatch
from app.core.models import Entry, Value


class MemoryStore:
    def __init__(self, initial_capacity: int, max_keys: int, default_ttl: int = 0) -> None:
        self._max_keys = max_keys
        self._default_ttl = default_ttl

        # Slot-based pre-allocation
        self._slots: list[Entry | None] = [None] * initial_capacity
        self._free: list[int] = list(range(initial_capacity - 1, -1, -1))
        self._key_index: dict[str, int] = {}

        # LRU doubly linked list (O(1) promote + evict)
        self._prev: dict[str, str | None] = {}  # key -> prev key (None if head)
        self._next: dict[str, str | None] = {}  # key -> next key (None if tail)
        self._head: str | None = None  # LRU — evict candidate
        self._tail: str | None = None  # MRU — most recently used

    # ------------------------------------------------------------------
    # LRU helpers
    # ------------------------------------------------------------------

    def _append_tail(self, key: str) -> None:
        """Add new key as MRU (tail)."""
        self._prev[key] = self._tail
        self._next[key] = None
        if self._tail is not None:
            self._next[self._tail] = key
        self._tail = key
        if self._head is None:
            self._head = key

    def _promote(self, key: str) -> None:
        """Move existing key to tail (most recently used)."""
        if self._tail == key:
            return
        prev_key = self._prev.get(key)
        next_key = self._next.get(key)

        if prev_key is not None:
            self._next[prev_key] = next_key
        else:
            self._head = next_key

        if next_key is not None:
            self._prev[next_key] = prev_key

        self._prev[key] = self._tail
        self._next[key] = None
        if self._tail is not None:
            self._next[self._tail] = key
        self._tail = key

    def _detach(self, key: str) -> None:
        """Remove key from LRU list (used on delete and eviction)."""
        prev_key = self._prev.pop(key, None)
        next_key = self._next.pop(key, None)

        if prev_key is not None:
            self._next[prev_key] = next_key
        else:
            self._head = next_key

        if next_key is not None:
            self._prev[next_key] = prev_key
        else:
            self._tail = prev_key

    def _evict_lru(self) -> None:
        """Remove the least recently used entry to free a slot."""
        if self._head is None:
            raise CapacityError("Store is full and has no entries to evict")
        victim = self._head
        slot = self._key_index.pop(victim)
        self._slots[slot] = None
        self._free.append(slot)
        self._detach(victim)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Entry:
        if key not in self._key_index:
            raise KeyNotFound(key)
        slot = self._key_index[key]
        entry = self._slots[slot]
        assert entry is not None

        if entry.expires_at is not None and _time.time() > entry.expires_at:
            # Lazy expiry: delete and raise
            self._slots[slot] = None
            self._free.append(slot)
            del self._key_index[key]
            self._detach(key)
            raise KeyNotFound(key)

        self._promote(key)
        return entry

    def set(self, key: str, value: Value, value_type: str, ttl: int | None) -> None:
        expires_at: float | None = None
        if ttl is not None and ttl > 0:
            expires_at = _time.time() + ttl
        elif self._default_ttl > 0:
            expires_at = _time.time() + self._default_ttl

        if key in self._key_index:
            slot = self._key_index[key]
            existing = self._slots[slot]
            assert existing is not None
            if existing.value_type != value_type:
                raise TypeMismatch(key, value_type, existing.value_type)
            self._slots[slot] = Entry(value=value, value_type=value_type, expires_at=expires_at)
            self._promote(key)
            return

        if len(self._key_index) >= self._max_keys:
            self._evict_lru()

        if not self._free:
            raise CapacityError("No free slots (call _grow first)")

        slot = self._free.pop()
        self._slots[slot] = Entry(value=value, value_type=value_type, expires_at=expires_at)
        self._key_index[key] = slot
        self._append_tail(key)

    def delete(self, key: str) -> None:
        if key not in self._key_index:
            raise KeyNotFound(key)
        slot = self._key_index.pop(key)
        self._slots[slot] = None
        self._free.append(slot)
        self._detach(key)

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
        self._promote(key)

    def expire(self, key: str, ttl: int) -> None:
        if key not in self._key_index:
            raise KeyNotFound(key)
        slot = self._key_index[key]
        existing = self._slots[slot]
        assert existing is not None
        self._slots[slot] = Entry(
            value=existing.value,
            value_type=existing.value_type,
            expires_at=_time.time() + ttl,
        )
        self._promote(key)

    def keys(self) -> list[str]:
        now = _time.time()
        expired = [
            k for k, idx in self._key_index.items()
            if (e := self._slots[idx]) is not None
            and e.expires_at is not None
            and now > e.expires_at
        ]
        for k in expired:
            slot = self._key_index.pop(k)
            self._slots[slot] = None
            self._free.append(slot)
            self._detach(k)
        return list(self._key_index.keys())

    def flush(self) -> None:
        size = len(self._slots)
        self._slots = [None] * size
        self._free = list(range(size - 1, -1, -1))
        self._key_index = {}
        self._prev = {}
        self._next = {}
        self._head = None
        self._tail = None
