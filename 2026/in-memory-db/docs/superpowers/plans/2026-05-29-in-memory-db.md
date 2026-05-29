# in-memory-db Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Redis-like in-memory key-value store with FastAPI REST API, LRU eviction, TTL, and hexagonal architecture.

**Architecture:** Hexagonal (ports & adapters) — pure domain core (`app/core/`) has zero FastAPI dependency; `StoragePort` Protocol decouples domain from REST adapter; REST is one adapter that can be swapped for gRPC by writing a new adapter.

**Tech Stack:** Python 3.12, UV, FastAPI, uvicorn, pydantic-settings, tomllib (stdlib), pytest, httpx, ruff, direnv, Taskfile

---

## File Map

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Project metadata + dependencies |
| `Taskfile.yml` | run, test, test-unit, lint, format, install |
| `config.toml` | Runtime defaults (store capacity, server host/port) |
| `.envrc` | direnv env vars (PYREDIS_HOST, PYREDIS_PORT override config) |
| `.python-version` | Python version pin |
| `.gitignore` | Ignore .venv, __pycache__, etc. |
| `app/__init__.py` | Empty |
| `app/core/exceptions.py` | `KeyNotFound`, `TypeMismatch`, `CapacityError` |
| `app/core/models.py` | `Entry` dataclass, `ValueType`, `Value` |
| `app/ports/storage.py` | `StoragePort` Protocol |
| `app/core/store.py` | `MemoryStore`: slots, free list, LRU linked list, TTL, grow |
| `app/config.py` | `StoreSettings`, `ServerSettings` (pydantic-settings) |
| `app/adapters/rest/schemas.py` | Pydantic request/response models |
| `app/adapters/rest/errors.py` | Exception → HTTP status handlers |
| `app/adapters/rest/router.py` | All FastAPI routes (synchronous) |
| `app/main.py` | App factory: loads config, wires DI, mounts router |
| `tests/conftest.py` | `store` and `client` fixtures |
| `tests/test_store.py` | Unit tests for `MemoryStore` (no FastAPI) |
| `tests/test_api.py` | Integration tests via httpx `TestClient` |
| `README.md` | Setup, config reference, API examples |
| `docs/scaling.md` | System design: sharding, replication, GCP |

---

## Task 1: Scaffold project

**Files:**
- Create: `pyproject.toml`
- Create: `Taskfile.yml`
- Create: `config.toml`
- Create: `.envrc`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `app/__init__.py`, `app/core/__init__.py`, `app/ports/__init__.py`, `app/adapters/__init__.py`, `app/adapters/rest/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p app/core app/ports app/adapters/rest tests docs/superpowers/plans
touch app/__init__.py app/core/__init__.py app/ports/__init__.py
touch app/adapters/__init__.py app/adapters/rest/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "in-memory-db"
version = "0.1.0"
description = "Redis-like in-memory key-value store"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.136.1",
    "uvicorn[standard]>=0.47.0",
    "pydantic-settings>=2.9.1",
]

[dependency-groups]
dev = [
    "httpx>=0.28.1",
    "pytest>=9.0.3",
    "ruff>=0.15.14",
]
```

- [ ] **Step 3: Write `Taskfile.yml`**

```yaml
version: "3"

tasks:
  run:
    desc: Start server with hot reload
    cmd: uv run uvicorn app.main:app --reload

  test:
    desc: Run all tests
    cmd: uv run pytest -v

  test-unit:
    desc: Run core store unit tests only
    cmd: uv run pytest tests/test_store.py -v

  lint:
    desc: Lint with ruff
    cmd: uv run ruff check .

  format:
    desc: Format with ruff
    cmd: uv run ruff format .

  install:
    desc: Install dependencies
    cmd: uv sync
```

- [ ] **Step 4: Write `config.toml`**

```toml
[store]
initial_capacity = 1000
max_keys = 10000
default_ttl_seconds = 0

[server]
host = "0.0.0.0"
port = 8000
```

- [ ] **Step 5: Write `.envrc`**

```bash
export PYREDIS_HOST=127.0.0.1
export PYREDIS_PORT=8000
```

- [ ] **Step 6: Write `.python-version`**

```
3.12
```

- [ ] **Step 7: Write `.gitignore`**

```
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info
.venv
```

- [ ] **Step 8: Install dependencies**

```bash
uv sync
```

Expected: lock file updated, `.venv` created.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml Taskfile.yml config.toml .envrc .python-version .gitignore app/ tests/
git commit -m "chore: scaffold in-memory-db project"
```

---

## Task 2: Core models, exceptions, StoragePort

**Files:**
- Create: `app/core/exceptions.py`
- Create: `app/core/models.py`
- Create: `app/ports/storage.py`
- Modify: `tests/test_store.py` (stub imports to verify they work)

- [ ] **Step 1: Write failing import test**

`tests/test_store.py`:
```python
from app.core.models import Entry, ValueType, Value
from app.core.exceptions import KeyNotFound, TypeMismatch, CapacityError
from app.ports.storage import StoragePort
```

- [ ] **Step 2: Run test to see it fail**

```bash
uv run pytest tests/test_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.models'`

- [ ] **Step 3: Write `app/core/exceptions.py`**

```python
class KeyNotFound(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Key not found: '{key}'")
        self.key = key


class TypeMismatch(Exception):
    def __init__(self, key: str, expected: str, got: str) -> None:
        super().__init__(f"Key '{key}' holds type '{got}', not '{expected}'")


class CapacityError(Exception): ...
```

- [ ] **Step 4: Write `app/core/models.py`**

```python
from dataclasses import dataclass
from typing import Literal

ValueType = Literal["string", "integer", "list", "hash"]
Value = str | int | list[str] | dict[str, str]


@dataclass
class Entry:
    value: Value
    value_type: ValueType
    expires_at: float | None = None  # Unix timestamp; None = no expiry
```

- [ ] **Step 5: Write `app/ports/storage.py`**

```python
from typing import Protocol
from app.core.models import Entry, Value


class StoragePort(Protocol):
    def get(self, key: str) -> Entry: ...
    def set(self, key: str, value: Value, value_type: str, ttl: int | None) -> None: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def update_value(self, key: str, value: Value) -> None: ...
    def expire(self, key: str, ttl: int) -> None: ...
    def keys(self) -> list[str]: ...
    def flush(self) -> None: ...
```

- [ ] **Step 6: Run test to see it pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: `1 passed` (the import-only test file has no test functions yet — pytest collects 0 tests and exits with no errors; add a placeholder):

Add to `tests/test_store.py`:
```python
def test_imports() -> None:
    assert Entry is not None
    assert StoragePort is not None
```

Run again: `1 passed`

- [ ] **Step 7: Commit**

```bash
git add app/core/exceptions.py app/core/models.py app/ports/storage.py tests/test_store.py
git commit -m "feat: add core models, exceptions, and StoragePort protocol"
```

---

## Task 3: MemoryStore — basic CRUD

**Files:**
- Create: `app/core/store.py`
- Modify: `tests/test_store.py`
- Create: `tests/conftest.py`

No LRU and no TTL yet. Raises `CapacityError` at `max_keys` (replaced by eviction in Task 4).

- [ ] **Step 1: Write failing tests**

Add to `tests/test_store.py`:

```python
import pytest
from app.core.store import MemoryStore
from app.core.exceptions import KeyNotFound, TypeMismatch, CapacityError


# --- fixtures ---

@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(initial_capacity=5, max_keys=5, default_ttl=0)


# --- basic CRUD ---

def test_set_get_string(store: MemoryStore) -> None:
    store.set("k", "hello", "string", ttl=None)
    entry = store.get("k")
    assert entry.value == "hello"
    assert entry.value_type == "string"


def test_set_get_integer(store: MemoryStore) -> None:
    store.set("k", 42, "integer", ttl=None)
    entry = store.get("k")
    assert entry.value == 42
    assert entry.value_type == "integer"


def test_set_get_list(store: MemoryStore) -> None:
    store.set("k", ["a", "b"], "list", ttl=None)
    entry = store.get("k")
    assert entry.value == ["a", "b"]
    assert entry.value_type == "list"


def test_set_get_hash(store: MemoryStore) -> None:
    store.set("k", {"f": "v"}, "hash", ttl=None)
    entry = store.get("k")
    assert entry.value == {"f": "v"}
    assert entry.value_type == "hash"


def test_get_missing_raises(store: MemoryStore) -> None:
    with pytest.raises(KeyNotFound):
        store.get("missing")


def test_delete(store: MemoryStore) -> None:
    store.set("k", "v", "string", ttl=None)
    store.delete("k")
    with pytest.raises(KeyNotFound):
        store.get("k")


def test_delete_missing_raises(store: MemoryStore) -> None:
    with pytest.raises(KeyNotFound):
        store.delete("missing")


def test_exists_true(store: MemoryStore) -> None:
    store.set("k", "v", "string", ttl=None)
    assert store.exists("k") is True


def test_exists_false(store: MemoryStore) -> None:
    assert store.exists("missing") is False


def test_keys(store: MemoryStore) -> None:
    store.set("a", "1", "string", ttl=None)
    store.set("b", "2", "string", ttl=None)
    assert set(store.keys()) == {"a", "b"}


def test_flush(store: MemoryStore) -> None:
    store.set("a", "1", "string", ttl=None)
    store.flush()
    assert store.keys() == []


def test_type_mismatch_raises(store: MemoryStore) -> None:
    store.set("k", "hello", "string", ttl=None)
    with pytest.raises(TypeMismatch):
        store.set("k", 42, "integer", ttl=None)


def test_overwrite_same_type(store: MemoryStore) -> None:
    store.set("k", "hello", "string", ttl=None)
    store.set("k", "world", "string", ttl=None)
    assert store.get("k").value == "world"


def test_update_value_preserves_type(store: MemoryStore) -> None:
    store.set("k", 10, "integer", ttl=None)
    store.update_value("k", 99)
    entry = store.get("k")
    assert entry.value == 99
    assert entry.value_type == "integer"


def test_update_value_missing_raises(store: MemoryStore) -> None:
    with pytest.raises(KeyNotFound):
        store.update_value("missing", 1)
```

- [ ] **Step 2: Run tests to see them fail**

```bash
uv run pytest tests/test_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.store'`

- [ ] **Step 3: Write `app/core/store.py`**

```python
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
        import time
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
```

- [ ] **Step 4: Run tests to see them pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: all CRUD tests pass. `test_imports` + all `test_set_get_*` + `test_delete*` + `test_exists*` + `test_keys` + `test_flush` + `test_type_mismatch*` + `test_overwrite*` + `test_update_value*` — **16 passed**.

- [ ] **Step 5: Commit**

```bash
git add app/core/store.py tests/test_store.py
git commit -m "feat: add MemoryStore with basic CRUD and slot pre-allocation"
```

---

## Task 4: MemoryStore — LRU eviction

**Files:**
- Modify: `app/core/store.py`
- Modify: `tests/test_store.py`

Adds doubly linked list (O(1) promote/evict). Replaces `CapacityError` at `max_keys` with LRU eviction.

- [ ] **Step 1: Write failing LRU test**

Add to `tests/test_store.py`:

```python
@pytest.fixture
def small_store() -> MemoryStore:
    """max_keys=3 forces eviction after 3 inserts."""
    return MemoryStore(initial_capacity=5, max_keys=3, default_ttl=0)


def test_lru_evicts_least_recently_used(small_store: MemoryStore) -> None:
    small_store.set("a", "1", "string", ttl=None)  # LRU order: [a]
    small_store.set("b", "2", "string", ttl=None)  # LRU order: [a, b]
    small_store.set("c", "3", "string", ttl=None)  # LRU order: [a, b, c] — at max_keys
    small_store.get("a")                            # promote a: [b, c, a]
    small_store.set("d", "4", "string", ttl=None)  # evict LRU=b; order: [c, a, d]

    with pytest.raises(KeyNotFound):
        small_store.get("b")  # b was evicted

    assert small_store.get("a").value == "1"
    assert small_store.get("c").value == "3"
    assert small_store.get("d").value == "4"


def test_lru_evicts_on_every_overflow(small_store: MemoryStore) -> None:
    for i in range(6):
        small_store.set(str(i), str(i), "string", ttl=None)
    # Only the 3 most recent (3, 4, 5) should remain
    assert set(small_store.keys()) == {"3", "4", "5"}
```

- [ ] **Step 2: Run tests to see them fail**

```bash
uv run pytest tests/test_store.py::test_lru_evicts_least_recently_used tests/test_store.py::test_lru_evicts_on_every_overflow -v
```

Expected: `CapacityError: Store is full` (current behaviour — no eviction yet).

- [ ] **Step 3: Rewrite `app/core/store.py` with LRU**

```python
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
        entry = self._slots[self._key_index[key]]
        assert entry is not None
        self._promote(key)
        return entry

    def set(self, key: str, value: Value, value_type: str, ttl: int | None) -> None:
        if key in self._key_index:
            slot = self._key_index[key]
            existing = self._slots[slot]
            assert existing is not None
            if existing.value_type != value_type:
                raise TypeMismatch(key, value_type, existing.value_type)
            self._slots[slot] = Entry(value=value, value_type=value_type, expires_at=existing.expires_at)
            self._promote(key)
            return

        if len(self._key_index) >= self._max_keys:
            self._evict_lru()

        if not self._free:
            raise CapacityError("No free slots (call _grow first)")

        slot = self._free.pop()
        self._slots[slot] = Entry(value=value, value_type=value_type)
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
```

- [ ] **Step 4: Run all store tests**

```bash
uv run pytest tests/test_store.py -v
```

Expected: all previous tests still pass + new LRU tests pass. **18 passed**.

- [ ] **Step 5: Commit**

```bash
git add app/core/store.py tests/test_store.py
git commit -m "feat: add O(1) LRU eviction to MemoryStore"
```

---

## Task 5: MemoryStore — TTL lazy expiry

**Files:**
- Modify: `app/core/store.py`
- Modify: `tests/test_store.py`

- [ ] **Step 1: Write failing TTL tests**

Add to `tests/test_store.py`:

```python
from unittest.mock import patch


def test_set_with_ttl_returns_value_before_expiry(store: MemoryStore) -> None:
    store.set("k", "v", "string", ttl=60)
    assert store.get("k").value == "v"


def test_expired_key_raises_key_not_found(store: MemoryStore) -> None:
    store.set("k", "v", "string", ttl=10)
    with patch("app.core.store._time") as mock_time:
        mock_time.time.return_value = _time.time() + 11
        with pytest.raises(KeyNotFound):
            store.get("k")


def test_expired_key_not_in_keys(store: MemoryStore) -> None:
    store.set("k", "v", "string", ttl=10)
    with patch("app.core.store._time") as mock_time:
        mock_time.time.return_value = _time.time() + 11
        assert "k" not in store.keys()


def test_expire_method_sets_ttl(store: MemoryStore) -> None:
    store.set("k", "v", "string", ttl=None)
    store.expire("k", ttl=10)
    with patch("app.core.store._time") as mock_time:
        mock_time.time.return_value = _time.time() + 11
        with pytest.raises(KeyNotFound):
            store.get("k")


def test_no_ttl_key_never_expires(store: MemoryStore) -> None:
    store.set("k", "v", "string", ttl=None)
    with patch("app.core.store._time") as mock_time:
        mock_time.time.return_value = _time.time() + 999_999
        assert store.get("k").value == "v"
```

Add at top of `tests/test_store.py` (after existing imports):
```python
import time as _time
```

- [ ] **Step 2: Run tests to see them fail**

```bash
uv run pytest tests/test_store.py::test_expired_key_raises_key_not_found -v
```

Expected: `AssertionError` — key is returned instead of raising `KeyNotFound` (no expiry check yet).

- [ ] **Step 3: Modify `get` and `set` in `app/core/store.py` to handle TTL**

Replace `get` method:
```python
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
```

Replace `set` method (add TTL calculation for new keys):
```python
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
```

Replace `keys` method to lazy-expire during scan:
```python
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
```

- [ ] **Step 4: Run all store tests**

```bash
uv run pytest tests/test_store.py -v
```

Expected: **23 passed**.

- [ ] **Step 5: Commit**

```bash
git add app/core/store.py tests/test_store.py
git commit -m "feat: add lazy TTL expiry to MemoryStore"
```

---

## Task 6: MemoryStore — dynamic grow

**Files:**
- Modify: `app/core/store.py`
- Modify: `tests/test_store.py`

- [ ] **Step 1: Write failing grow test**

Add to `tests/test_store.py`:

```python
def test_grow_beyond_initial_capacity() -> None:
    # initial_capacity=2, max_keys=10 — store must grow when slots run out
    store = MemoryStore(initial_capacity=2, max_keys=10, default_ttl=0)
    for i in range(6):
        store.set(str(i), str(i), "string", ttl=None)
    for i in range(6):
        assert store.get(str(i)).value == str(i)
    assert len(store.keys()) == 6
```

- [ ] **Step 2: Run test to see it fail**

```bash
uv run pytest tests/test_store.py::test_grow_beyond_initial_capacity -v
```

Expected: `CapacityError: No free slots` after inserting 2 keys.

- [ ] **Step 3: Add `_grow` and call it in `set`**

Add `_grow` method to `MemoryStore` (before `get`):
```python
def _grow(self) -> None:
    """Double slot capacity."""
    old_size = len(self._slots)
    self._slots.extend([None] * old_size)
    # Add new slot indices in reverse so pop() gives lowest index first
    self._free.extend(range(2 * old_size - 1, old_size - 1, -1))
```

In `set`, replace the `if not self._free: raise CapacityError(...)` block with:
```python
if not self._free:
    self._grow()
```

- [ ] **Step 4: Run all store tests**

```bash
uv run pytest tests/test_store.py -v
```

Expected: **24 passed**.

- [ ] **Step 5: Commit**

```bash
git add app/core/store.py tests/test_store.py
git commit -m "feat: add dynamic slot growth to MemoryStore"
```

---

## Task 7: Config

**Files:**
- Create: `app/config.py`

- [ ] **Step 1: Write `app/config.py`**

```python
import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_toml(section: str) -> dict:
    path = Path("config.toml")
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f).get(section, {})


class StoreSettings(BaseSettings):
    initial_capacity: int = 1000
    max_keys: int = 10000
    default_ttl_seconds: int = 0

    @classmethod
    def from_toml(cls) -> "StoreSettings":
        return cls(**_load_toml("store"))


class ServerSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    model_config = SettingsConfigDict(env_prefix="PYREDIS_")

    @classmethod
    def from_toml_and_env(cls) -> "ServerSettings":
        toml_vals = _load_toml("server")
        return cls(**toml_vals)  # env vars (PYREDIS_*) override via pydantic-settings
```

- [ ] **Step 2: Verify config loads without error**

```bash
uv run python -c "
from app.config import StoreSettings, ServerSettings
s = StoreSettings.from_toml()
srv = ServerSettings.from_toml_and_env()
print(s)
print(srv)
"
```

Expected output (values from `config.toml` unless `PYREDIS_HOST`/`PYREDIS_PORT` set in env):
```
StoreSettings(initial_capacity=1000, max_keys=10000, default_ttl_seconds=0)
ServerSettings(host='127.0.0.1', port=8000)
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py
git commit -m "feat: add pydantic-settings config with TOML + env var support"
```

---

## Task 8: REST schemas

**Files:**
- Create: `app/adapters/rest/schemas.py`

- [ ] **Step 1: Write `app/adapters/rest/schemas.py`**

```python
from pydantic import BaseModel


# --- Request models ---

class StringSetRequest(BaseModel):
    value: str
    ttl: int | None = None


class IntegerSetRequest(BaseModel):
    value: int
    ttl: int | None = None


class ListSetRequest(BaseModel):
    value: list[str]
    ttl: int | None = None


class HashSetRequest(BaseModel):
    value: dict[str, str]
    ttl: int | None = None


class IncrRequest(BaseModel):
    delta: int = 1


class ListPushRequest(BaseModel):
    item: str


class HashFieldSetRequest(BaseModel):
    field: str
    value: str


class HashFieldGetRequest(BaseModel):
    field: str


class ExpireRequest(BaseModel):
    ttl: int


# --- Response models ---

class EntryResponse(BaseModel):
    key: str
    value: str | int | list[str] | dict[str, str]
    type: str
    ttl_remaining: float | None = None


class KeysResponse(BaseModel):
    keys: list[str]


class ListPopResponse(BaseModel):
    value: str


class HashFieldResponse(BaseModel):
    field: str
    value: str
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from app.adapters.rest.schemas import EntryResponse; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add app/adapters/rest/schemas.py
git commit -m "feat: add REST request/response schemas"
```

---

## Task 9: Error handlers + app factory (skeleton)

**Files:**
- Create: `app/adapters/rest/errors.py`
- Create: `app/adapters/rest/router.py` (skeleton)
- Create: `app/main.py`

- [ ] **Step 1: Write `app/adapters/rest/errors.py`**

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import CapacityError, KeyNotFound, TypeMismatch


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(KeyNotFound)
    def handle_key_not_found(request: Request, exc: KeyNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TypeMismatch)
    def handle_type_mismatch(request: Request, exc: TypeMismatch) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(CapacityError)
    def handle_capacity_error(request: Request, exc: CapacityError) -> JSONResponse:
        return JSONResponse(status_code=507, content={"detail": str(exc)})
```

- [ ] **Step 2: Write skeleton `app/adapters/rest/router.py`**

```python
from fastapi import APIRouter, Depends
from app.ports.storage import StoragePort


router = APIRouter()


def get_store() -> StoragePort:
    raise NotImplementedError("get_store dependency must be overridden")
```

- [ ] **Step 3: Write `app/main.py`**

```python
from fastapi import FastAPI

from app.adapters.rest.errors import register_error_handlers
from app.adapters.rest.router import get_store, router
from app.config import StoreSettings, ServerSettings
from app.core.store import MemoryStore
from app.ports.storage import StoragePort


def create_app(store: StoragePort | None = None) -> FastAPI:
    app = FastAPI(title="in-memory-db")

    if store is None:
        cfg = StoreSettings.from_toml()
        store = MemoryStore(
            initial_capacity=cfg.initial_capacity,
            max_keys=cfg.max_keys,
            default_ttl=cfg.default_ttl_seconds,
        )

    app.dependency_overrides[get_store] = lambda: store
    app.include_router(router)
    register_error_handlers(app)

    return app


app = create_app()
```

- [ ] **Step 4: Verify server starts**

```bash
uv run uvicorn app.main:app --reload
```

Expected: `Uvicorn running on http://127.0.0.1:8000` (no errors). Ctrl+C to stop.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/rest/errors.py app/adapters/rest/router.py app/main.py
git commit -m "feat: add FastAPI app factory, error handlers, and DI wiring"
```

---

## Task 10: REST router — read + delete endpoints

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_api.py`
- Modify: `app/adapters/rest/router.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient

from app.core.store import MemoryStore
from app.main import create_app


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(initial_capacity=5, max_keys=5, default_ttl=0)


@pytest.fixture
def small_store() -> MemoryStore:
    return MemoryStore(initial_capacity=5, max_keys=3, default_ttl=0)


@pytest.fixture
def client(store: MemoryStore) -> TestClient:
    return TestClient(create_app(store=store))
```

> **Note:** The `store` fixture in `conftest.py` supersedes the local `store` fixture in `test_store.py`. Remove the local `store` fixture from `test_store.py` and keep only `small_store` local to that file. The `conftest.py` `store` (5 cap / 5 max) will be used by `test_store.py` tests that request `store`.

- [ ] **Step 2: Remove local `store` fixture from `tests/test_store.py`**

Delete these lines from `tests/test_store.py`:
```python
@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(initial_capacity=5, max_keys=5, default_ttl=0)
```

- [ ] **Step 3: Write failing read/delete tests in `tests/test_api.py`**

```python
import pytest
from fastapi.testclient import TestClient


def test_list_keys_empty(client: TestClient) -> None:
    resp = client.get("/keys")
    assert resp.status_code == 200
    assert resp.json() == {"keys": []}


def test_list_keys_after_insert(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.get("/keys")
    assert "foo" in resp.json()["keys"]


def test_get_key_string(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.get("/keys/foo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "foo"
    assert data["value"] == "bar"
    assert data["type"] == "string"
    assert data["ttl_remaining"] is None


def test_get_key_with_ttl(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar", "ttl": 60})
    resp = client.get("/keys/foo")
    assert 0 < resp.json()["ttl_remaining"] <= 60


def test_get_key_not_found(client: TestClient) -> None:
    resp = client.get("/keys/missing")
    assert resp.status_code == 404


def test_delete_key(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.delete("/keys/foo")
    assert resp.status_code == 204
    assert client.get("/keys/foo").status_code == 404


def test_delete_key_not_found(client: TestClient) -> None:
    resp = client.delete("/keys/missing")
    assert resp.status_code == 404


def test_flush(client: TestClient) -> None:
    client.post("/keys/a/string", json={"value": "1"})
    client.post("/keys/b/string", json={"value": "2"})
    resp = client.delete("/keys")
    assert resp.status_code == 204
    assert client.get("/keys").json() == {"keys": []}
```

- [ ] **Step 4: Run tests to see them fail**

```bash
uv run pytest tests/test_api.py -v
```

Expected: `404 Not Found` for all routes (router is skeleton with no handlers yet).

- [ ] **Step 5: Implement read/delete handlers in `app/adapters/rest/router.py`**

```python
import time

from fastapi import APIRouter, Depends, Response

from app.adapters.rest.schemas import EntryResponse, KeysResponse
from app.core.exceptions import TypeMismatch
from app.ports.storage import StoragePort


router = APIRouter()


def get_store() -> StoragePort:
    raise NotImplementedError("get_store dependency must be overridden")


def _entry_response(key: str, store: StoragePort) -> EntryResponse:
    entry = store.get(key)
    ttl_remaining: float | None = None
    if entry.expires_at is not None:
        ttl_remaining = max(0.0, entry.expires_at - time.time())
    return EntryResponse(key=key, value=entry.value, type=entry.value_type, ttl_remaining=ttl_remaining)


@router.get("/keys", response_model=KeysResponse)
def list_keys(store: StoragePort = Depends(get_store)) -> KeysResponse:
    return KeysResponse(keys=store.keys())


@router.delete("/keys", status_code=204)
def flush(store: StoragePort = Depends(get_store)) -> Response:
    store.flush()
    return Response(status_code=204)


@router.get("/keys/{key}", response_model=EntryResponse)
def get_key(key: str, store: StoragePort = Depends(get_store)) -> EntryResponse:
    return _entry_response(key, store)


@router.delete("/keys/{key}", status_code=204)
def delete_key(key: str, store: StoragePort = Depends(get_store)) -> Response:
    store.delete(key)
    return Response(status_code=204)
```

- [ ] **Step 6: Run API tests**

```bash
uv run pytest tests/test_api.py -v
```

Expected: read/delete tests pass. Write-endpoint tests don't exist yet. **8 passed**.

- [ ] **Step 7: Run full test suite**

```bash
uv run pytest -v
```

Expected: all store unit tests + 8 API tests pass. No regressions.

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py tests/test_api.py tests/test_store.py app/adapters/rest/router.py
git commit -m "feat: add REST read and delete endpoints with integration tests"
```

---

## Task 11: REST router — write + mutation endpoints

**Files:**
- Modify: `tests/test_api.py`
- Modify: `app/adapters/rest/router.py`

- [ ] **Step 1: Write failing write/mutation tests**

Append to `tests/test_api.py`:

```python
# --- POST set endpoints ---

def test_set_integer(client: TestClient) -> None:
    resp = client.post("/keys/count/integer", json={"value": 10})
    assert resp.status_code == 200
    assert client.get("/keys/count").json()["value"] == 10


def test_set_list(client: TestClient) -> None:
    resp = client.post("/keys/mylist/list", json={"value": ["a", "b"]})
    assert resp.status_code == 200
    assert client.get("/keys/mylist").json()["value"] == ["a", "b"]


def test_set_hash(client: TestClient) -> None:
    resp = client.post("/keys/myhash/hash", json={"value": {"name": "alice"}})
    assert resp.status_code == 200
    assert client.get("/keys/myhash").json()["value"] == {"name": "alice"}


def test_set_type_mismatch_returns_409(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.post("/keys/foo/integer", json={"value": 42})
    assert resp.status_code == 409


# --- PATCH integer/incr ---

def test_incr(client: TestClient) -> None:
    client.post("/keys/count/integer", json={"value": 10})
    resp = client.patch("/keys/count/integer/incr", json={"delta": 5})
    assert resp.status_code == 200
    assert client.get("/keys/count").json()["value"] == 15


def test_incr_default_delta(client: TestClient) -> None:
    client.post("/keys/count/integer", json={"value": 0})
    client.patch("/keys/count/integer/incr", json={})
    assert client.get("/keys/count").json()["value"] == 1


def test_incr_type_mismatch(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.patch("/keys/foo/integer/incr", json={"delta": 1})
    assert resp.status_code == 409


# --- PATCH list/push + list/pop ---

def test_list_push(client: TestClient) -> None:
    client.post("/keys/mylist/list", json={"value": ["a"]})
    client.patch("/keys/mylist/list/push", json={"item": "b"})
    assert client.get("/keys/mylist").json()["value"] == ["a", "b"]


def test_list_pop(client: TestClient) -> None:
    client.post("/keys/mylist/list", json={"value": ["a", "b"]})
    resp = client.patch("/keys/mylist/list/pop")
    assert resp.status_code == 200
    assert resp.json()["value"] == "b"
    assert client.get("/keys/mylist").json()["value"] == ["a"]


# --- PATCH hash/set + hash/get ---

def test_hash_field_set(client: TestClient) -> None:
    client.post("/keys/myhash/hash", json={"value": {}})
    client.patch("/keys/myhash/hash/set", json={"field": "name", "value": "alice"})
    assert client.get("/keys/myhash").json()["value"]["name"] == "alice"


def test_hash_field_get(client: TestClient) -> None:
    client.post("/keys/myhash/hash", json={"value": {"name": "alice"}})
    resp = client.patch("/keys/myhash/hash/get", json={"field": "name"})
    assert resp.status_code == 200
    assert resp.json()["value"] == "alice"


def test_hash_field_get_missing_field(client: TestClient) -> None:
    client.post("/keys/myhash/hash", json={"value": {}})
    resp = client.patch("/keys/myhash/hash/get", json={"field": "nope"})
    assert resp.status_code == 404


# --- PATCH expire ---

def test_expire_endpoint(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.patch("/keys/foo/expire", json={"ttl": 60})
    assert resp.status_code == 200
    assert 0 < client.get("/keys/foo").json()["ttl_remaining"] <= 60
```

- [ ] **Step 2: Run to see failures**

```bash
uv run pytest tests/test_api.py -v
```

Expected: new tests fail with `404 Method Not Allowed` or `422`.

- [ ] **Step 3: Add write/mutation handlers to `app/adapters/rest/router.py`**

Add after the existing handlers:

```python
from app.adapters.rest.schemas import (
    EntryResponse,
    ExpireRequest,
    HashFieldGetRequest,
    HashFieldResponse,
    HashFieldSetRequest,
    HashSetRequest,
    IncrRequest,
    IntegerSetRequest,
    KeysResponse,
    ListPopResponse,
    ListPushRequest,
    ListSetRequest,
    StringSetRequest,
)
from app.core.exceptions import KeyNotFound, TypeMismatch


@router.post("/keys/{key}/string", response_model=EntryResponse)
def set_string(key: str, body: StringSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "string", ttl=body.ttl)
    return _entry_response(key, store)


@router.post("/keys/{key}/integer", response_model=EntryResponse)
def set_integer(key: str, body: IntegerSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "integer", ttl=body.ttl)
    return _entry_response(key, store)


@router.post("/keys/{key}/list", response_model=EntryResponse)
def set_list(key: str, body: ListSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "list", ttl=body.ttl)
    return _entry_response(key, store)


@router.post("/keys/{key}/hash", response_model=EntryResponse)
def set_hash(key: str, body: HashSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "hash", ttl=body.ttl)
    return _entry_response(key, store)


@router.patch("/keys/{key}/integer/incr", response_model=EntryResponse)
def incr_integer(key: str, body: IncrRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    entry = store.get(key)
    if entry.value_type != "integer":
        raise TypeMismatch(key, "integer", entry.value_type)
    store.update_value(key, int(entry.value) + body.delta)
    return _entry_response(key, store)


@router.patch("/keys/{key}/list/push", response_model=EntryResponse)
def list_push(key: str, body: ListPushRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    entry = store.get(key)
    if entry.value_type != "list":
        raise TypeMismatch(key, "list", entry.value_type)
    store.update_value(key, list(entry.value) + [body.item])
    return _entry_response(key, store)


@router.patch("/keys/{key}/list/pop", response_model=ListPopResponse)
def list_pop(key: str, store: StoragePort = Depends(get_store)) -> ListPopResponse:
    entry = store.get(key)
    if entry.value_type != "list":
        raise TypeMismatch(key, "list", entry.value_type)
    lst = list(entry.value)
    if not lst:
        raise KeyNotFound(key)
    item = lst.pop()
    store.update_value(key, lst)
    return ListPopResponse(value=item)


@router.patch("/keys/{key}/hash/set", response_model=EntryResponse)
def hash_field_set(
    key: str, body: HashFieldSetRequest, store: StoragePort = Depends(get_store)
) -> EntryResponse:
    entry = store.get(key)
    if entry.value_type != "hash":
        raise TypeMismatch(key, "hash", entry.value_type)
    updated = dict(entry.value) | {body.field: body.value}
    store.update_value(key, updated)
    return _entry_response(key, store)


@router.patch("/keys/{key}/hash/get", response_model=HashFieldResponse)
def hash_field_get(
    key: str, body: HashFieldGetRequest, store: StoragePort = Depends(get_store)
) -> HashFieldResponse:
    entry = store.get(key)
    if entry.value_type != "hash":
        raise TypeMismatch(key, "hash", entry.value_type)
    h = dict(entry.value)
    if body.field not in h:
        raise KeyNotFound(body.field)
    return HashFieldResponse(field=body.field, value=h[body.field])


@router.patch("/keys/{key}/expire", response_model=EntryResponse)
def expire_key(key: str, body: ExpireRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.expire(key, body.ttl)
    return _entry_response(key, store)
```

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass. Should be **40+ passed, 0 failed**.

- [ ] **Step 5: Lint**

```bash
uv run ruff check .
```

Fix any issues reported, then re-run until clean.

- [ ] **Step 6: Commit**

```bash
git add tests/test_api.py app/adapters/rest/router.py
git commit -m "feat: add REST write and mutation endpoints with integration tests"
```

---

## Task 12: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# in-memory-db

Redis-like in-memory key-value store with a REST API, LRU eviction, and per-key TTL.

## Stack

- Python 3.12, [UV](https://docs.astral.sh/uv/), FastAPI, uvicorn
- pydantic-settings (config + env var overrides)
- pytest + httpx (tests)
- ruff (lint/format)
- Taskfile (task runner)
- direnv (env var management)

## Architecture

Hexagonal (ports & adapters). The domain (`app/core/`) has zero FastAPI dependency.
`StoragePort` (Protocol) decouples business logic from transport.
Swap REST for gRPC by writing a new adapter — no domain changes needed.

```
app/
  core/          ← pure Python domain: store, models, exceptions
  ports/         ← StoragePort Protocol
  adapters/rest/ ← FastAPI adapter (current)
```

## Setup

```bash
# Install dependencies
task install        # or: uv sync

# Configure (optional — direnv auto-loads .envrc)
direnv allow

# Start server (hot reload)
task run
```

## Configuration

`config.toml` sets defaults. `PYREDIS_HOST` and `PYREDIS_PORT` env vars override server settings.

| Key | Default | Description |
|-----|---------|-------------|
| `store.initial_capacity` | 1000 | Pre-allocated slot count |
| `store.max_keys` | 10000 | Hard cap; LRU evicts when reached |
| `store.default_ttl_seconds` | 0 | Global TTL (0 = no expiry) |
| `server.host` | 0.0.0.0 | Server bind host |
| `server.port` | 8000 | Server bind port |

## API

Base path: `/keys`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/keys` | List all live keys |
| `DELETE` | `/keys` | Flush all entries |
| `GET` | `/keys/{key}` | Get value, type, TTL |
| `DELETE` | `/keys/{key}` | Delete key |
| `POST` | `/keys/{key}/string` | Set string value |
| `POST` | `/keys/{key}/integer` | Set integer value |
| `POST` | `/keys/{key}/list` | Set list value |
| `POST` | `/keys/{key}/hash` | Set hash value |
| `PATCH` | `/keys/{key}/integer/incr` | Increment integer |
| `PATCH` | `/keys/{key}/list/push` | Append to list |
| `PATCH` | `/keys/{key}/list/pop` | Pop last item |
| `PATCH` | `/keys/{key}/hash/set` | Set hash field |
| `PATCH` | `/keys/{key}/hash/get` | Get hash field |
| `PATCH` | `/keys/{key}/expire` | Set/reset TTL |

### Examples

```bash
# Set a string with 60s TTL
curl -X POST http://localhost:8000/keys/greeting/string \
  -H "Content-Type: application/json" \
  -d '{"value": "hello", "ttl": 60}'

# Get it
curl http://localhost:8000/keys/greeting
# {"key":"greeting","value":"hello","type":"string","ttl_remaining":59.8}

# Increment a counter
curl -X POST http://localhost:8000/keys/hits/integer -d '{"value": 0}'
curl -X PATCH http://localhost:8000/keys/hits/integer/incr -d '{"delta": 1}'

# List operations
curl -X POST http://localhost:8000/keys/queue/list -d '{"value": ["task1"]}'
curl -X PATCH http://localhost:8000/keys/queue/list/push -d '{"item": "task2"}'
curl -X PATCH http://localhost:8000/keys/queue/list/pop
```

## Running tests

```bash
task test           # all tests
task test-unit      # store unit tests only (no FastAPI)
```

## Linting

```bash
task lint
task format
```

## Scaling

See [docs/scaling.md](docs/scaling.md) for how this would extend to a multi-node production system.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, config reference, and API examples"
```

---

## Task 13: docs/scaling.md — system design doc

**Files:**
- Create: `docs/scaling.md`

- [ ] **Step 1: Write `docs/scaling.md`**

````markdown
# Scaling in-memory-db to Production

This document outlines how the single-node `in-memory-db` would evolve into a
production-grade distributed system, and answers likely interview questions about
scalability, fault tolerance, and cloud deployment.

---

## Current limitations (single node)

| Constraint | Impact |
|-----------|--------|
| All data in one process | Limited by single machine RAM |
| No replication | Single point of failure |
| No persistence | Data lost on restart |
| Background TTL not swept | Expired slots occupy RAM until next read |

---

## 1. Background TTL sweep (near-term)

Add a daemon thread that periodically scans `_key_index` for expired entries and
frees their slots. Configurable sweep interval (e.g., every 1 second).

```python
import threading

class MemoryStore:
    def _start_ttl_sweep(self, interval: float = 1.0) -> None:
        def sweep():
            while True:
                self.keys()   # lazy expiry already cleans up expired keys
                time.sleep(interval)
        t = threading.Thread(target=sweep, daemon=True)
        t.start()
```

**Trade-off:** Adds CPU overhead on sweep thread. Configurable interval balances
freshness vs. CPU cost.

---

## 2. Persistence

Two strategies (mirrors Redis):

### AOF (Append-Only File)
Every write command is appended to a log file. On restart, replay the log to
rebuild state. Low data loss (lose at most the last `fsync` interval).

### RDB Snapshot
Periodically serialise the full `_key_index` + `_slots` to disk (e.g., via
`pickle` or `msgpack`). Faster restarts than AOF replay, but potential for data
loss between snapshots.

**GCP implementation:** Store snapshots/AOF in **Google Cloud Storage** (GCS).
On GKE pod restart, download the latest snapshot before serving traffic.
Use a GCS bucket lifecycle policy to retain only the last N snapshots.

---

## 3. Multi-node: sharding

Sharding distributes keys across N nodes so each node owns `total_keys / N` keys.

### Consistent hashing

Assign each node a set of positions on a virtual ring (e.g., using `hashlib.md5`
of the node ID). Route each key to the node whose ring position is the nearest
clockwise successor of `hash(key)`.

```python
import hashlib
import bisect

class ConsistentHashRing:
    def __init__(self, nodes: list[str], replicas: int = 150) -> None:
        self._ring: dict[int, str] = {}
        self._sorted_keys: list[int] = []
        for node in nodes:
            for i in range(replicas):
                h = int(hashlib.md5(f"{node}-{i}".encode()).hexdigest(), 16)
                self._ring[h] = node
                bisect.insort(self._sorted_keys, h)

    def get_node(self, key: str) -> str:
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        idx = bisect.bisect_right(self._sorted_keys, h) % len(self._sorted_keys)
        return self._ring[self._sorted_keys[idx]]
```

**Client-side routing:** A thin proxy/sidecar (or the client SDK) calls
`ring.get_node(key)` and forwards the request to the correct node.

**GCP implementation:** Deploy each shard as a **GKE Deployment** (1+ replicas
behind a ClusterIP Service). A routing layer (e.g., Envoy, or a simple FastAPI
proxy) resolves the shard and proxies the request.

---

## 4. Replication (fault tolerance)

Each shard runs a **leader** and 1-2 **followers**:

- All writes go to the leader.
- Leader replicates writes to followers asynchronously (or synchronously for
  strong consistency).
- If leader fails, a follower is elected via a consensus protocol (Raft) or a
  simple heartbeat + ZooKeeper/etcd lease.

**GCP implementation:** Use **GKE StatefulSets** (stable pod identities) for
leader/follower roles. Use **Cloud Spanner** or **etcd on GKE** for leader
election coordination.

---

## 5. Auto-scaling

### Vertical (single node)
Increase pod memory limits in GKE. Adjust `max_keys` and `initial_capacity` in
`config.toml` at deploy time via a ConfigMap.

### Horizontal (add shards)
Adding a new shard requires re-distributing keys:

1. Add the new node to the consistent hash ring.
2. The affected key range (roughly `total_keys / (N+1)`) migrates from the
   existing owner to the new node.
3. Use a short dual-write period during migration.

**GCP implementation:** Use **GKE Horizontal Pod Autoscaler** on a custom metric
(e.g., Prometheus `memory_used_ratio`). When a shard pod's memory crosses a
threshold, trigger a shard-split operation.

---

## 6. gRPC adapter

The `StoragePort` Protocol makes swapping transports trivial. A gRPC adapter:

1. Define a `.proto` schema matching the `StoragePort` interface.
2. Implement a gRPC servicer that calls `MemoryStore` methods.
3. No changes to `app/core/` — only a new `app/adapters/grpc/` package.

**When to prefer gRPC over REST:** Lower latency (binary framing, multiplexed
HTTP/2), streaming (e.g., subscribe to key changes), and strong schema contracts
across polyglot clients.

---

## 7. Observability

- **Prometheus metrics** (via `prometheus-fastapi-instrumentator`): request
  latency, cache hit/miss rate, eviction count, key count.
- **Cloud Monitoring** (GCP): export Prometheus metrics to Cloud Monitoring via
  the managed collection agent on GKE.
- **Cloud Trace**: distributed tracing across the proxy → shard hops.
- **Structured logging**: emit JSON logs via Python `logging` + Cloud Logging.

---

## Summary: production architecture on GCP

```
Client
  │
  ▼
Cloud Load Balancer
  │
  ▼
GKE: Routing Proxy (FastAPI / Envoy)
  │   Consistent hash ring → shard selection
  ├──► GKE: Shard 0 (StatefulSet: leader + follower)
  ├──► GKE: Shard 1 (StatefulSet: leader + follower)
  └──► GKE: Shard N ...
           │
           ▼
        GCS: Snapshots / AOF logs
           │
           ▼
        Cloud Monitoring / Cloud Trace
```
````

- [ ] **Step 2: Commit**

```bash
git add docs/scaling.md
git commit -m "docs: add multi-node scaling and GCP production design"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 14 REST endpoints covered (Tasks 10–11). LRU (Task 4). TTL (Task 5). Grow (Task 6). TOML config + env override (Task 7). Pydantic schemas (Task 8). Error handlers (Task 9). README (Task 12). scaling.md (Task 13). Taskfile with `test-unit` and watch mode (`--reload`). direnv `.envrc`.
- [x] **No placeholders:** All code steps are complete and runnable.
- [x] **Type consistency:** `Entry`, `Value`, `ValueType`, `StoragePort`, `MemoryStore` — defined in Tasks 2–3, used consistently in Tasks 4–11. `KeyNotFound(key: str)`, `TypeMismatch(key, expected, got)` — consistent across store and router.
- [x] **`update_value`** defined in Task 3, used in Task 11 router mutation handlers.
- [x] **`_entry_response`** helper defined in Task 10, used in Task 11.
- [x] **import `time as _time`** in `store.py` — mocked as `app.core.store._time` in TTL tests (Task 5). Consistent.
