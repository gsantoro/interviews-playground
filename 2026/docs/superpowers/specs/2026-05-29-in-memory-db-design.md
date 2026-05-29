# in-memory-db — Design Spec

**Date:** 2026-05-29
**Project:** `in-memory-db` — Redis-like in-memory key-value store
**Stack:** Python 3.12, UV, FastAPI, uvicorn, pydantic-settings, pytest, ruff, direnv, Taskfile

---

## Overview

Single-node, in-memory key-value store exposing a REST API. Supports four value types (string, integer, list, hash), per-key TTL with lazy expiry, and LRU eviction when `max_keys` is reached. Clean hexagonal architecture separates domain logic from the REST adapter so the API layer can be swapped for gRPC or any other transport without touching core logic.

---

## Project Structure

```
in-memory-db/
├── pyproject.toml
├── Taskfile.yml
├── config.toml
├── .envrc
├── .python-version
├── .gitignore
├── README.md
├── docs/
│   └── scaling.md
├── app/
│   ├── main.py               # FastAPI app factory; loads config; wires DI
│   ├── config.py             # pydantic-settings: StoreSettings, ServerSettings
│   ├── core/
│   │   ├── models.py         # Entry dataclass, ValueType, Value union
│   │   ├── store.py          # MemoryStore: LRU + TTL + pre-alloc logic
│   │   └── exceptions.py     # KeyNotFound, TypeMismatch, CapacityError
│   ├── ports/
│   │   └── storage.py        # StoragePort Protocol
│   └── adapters/
│       └── rest/
│           ├── router.py     # FastAPI routes (no async)
│           ├── schemas.py    # Pydantic request/response models
│           └── errors.py     # Exception → HTTP status handlers
└── tests/
    ├── conftest.py
    ├── test_store.py
    └── test_api.py
```

---

## Configuration

### `config.toml` (defaults)

```toml
[store]
initial_capacity = 1000    # slots pre-allocated at startup
max_keys = 10000           # hard cap; LRU evicts when reached
default_ttl_seconds = 0    # 0 = no TTL unless explicitly set per key

[server]
host = "0.0.0.0"
port = 8000
```

`initial_capacity < max_keys`. The store pre-allocates `initial_capacity` slots and grows by doubling when slots run out, up to `max_keys`.

### `.envrc` (direnv — overrides config.toml for server)

```bash
export PYREDIS_HOST=127.0.0.1
export PYREDIS_PORT=8000
```

### `app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class StoreSettings(BaseSettings):
    initial_capacity: int = 1000
    max_keys: int = 10000
    default_ttl_seconds: int = 0

class ServerSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    model_config = SettingsConfigDict(env_prefix="PYREDIS_")
```

---

## Core Domain

### `app/core/models.py`

```python
from dataclasses import dataclass, field
from typing import Literal

ValueType = Literal["string", "integer", "list", "hash"]
Value = str | int | list[str] | dict[str, str]

@dataclass
class Entry:
    value: Value
    value_type: ValueType
    expires_at: float | None = None  # Unix timestamp; None = immortal
```

### `app/core/exceptions.py`

```python
class KeyNotFound(Exception): ...
class TypeMismatch(Exception): ...
class CapacityError(Exception): ...
```

### `app/ports/storage.py`

```python
from typing import Protocol
from app.core.models import Entry, Value

class StoragePort(Protocol):
    def get(self, key: str) -> Entry: ...           # raises KeyNotFound if missing/expired
    def set(self, key: str, value: Value, value_type: str, ttl: int | None) -> None: ...
    def delete(self, key: str) -> None: ...         # raises KeyNotFound
    def exists(self, key: str) -> bool: ...
    def expire(self, key: str, ttl: int) -> None: ...
    def keys(self) -> list[str]: ...
    def flush(self) -> None: ...
```

### `app/core/store.py` — MemoryStore

**Pre-allocation:**
- `_slots: list[Entry | None]` — sized to `initial_capacity` at init
- `_free: list[int]` — stack of free slot indices (`list(range(initial_capacity))`)
- `_key_index: dict[str, int]` — key → slot index

When `_free` is empty and `len(_key_index) < max_keys`: double `_slots` and extend `_free` with new indices.
When `len(_key_index) == max_keys`: evict LRU before inserting.

**LRU — doubly linked list on dicts (O(1) promote + evict):**
- `_prev: dict[str, str | None]`
- `_next: dict[str, str | None]`
- `_head: str | None` — least recently used (evict candidate)
- `_tail: str | None` — most recently used

On `get`: promote key to tail. On `set` (new key): append to tail. On evict: remove head, free its slot.

**TTL — lazy expiry:**
- On every `get`: check `entry.expires_at`. If `time.time() > expires_at`: delete entry, raise `KeyNotFound`.
- No background thread. Document as future work in `docs/scaling.md`.

---

## REST API

Base path: `/keys`. All handlers synchronous (no `async def`).

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/keys` | List all live keys |
| `DELETE` | `/keys` | Flush all entries |
| `GET` | `/keys/{key}` | Get entry: value + type + ttl_remaining |
| `DELETE` | `/keys/{key}` | Delete key (404 if missing) |
| `POST` | `/keys/{key}/string` | Set string value |
| `POST` | `/keys/{key}/integer` | Set integer value |
| `POST` | `/keys/{key}/list` | Set list value |
| `POST` | `/keys/{key}/hash` | Set hash value |
| `PATCH` | `/keys/{key}/integer/incr` | Increment integer by delta |
| `PATCH` | `/keys/{key}/list/push` | Append item to list |
| `PATCH` | `/keys/{key}/list/pop` | Remove and return last item |
| `PATCH` | `/keys/{key}/hash/set` | Set a field in hash |
| `PATCH` | `/keys/{key}/hash/get` | Get a field from hash |
| `PATCH` | `/keys/{key}/expire` | Set/reset TTL on existing key |

### Request/Response (examples)

```json
// POST /keys/foo/string
{ "value": "hello", "ttl": 60 }

// GET /keys/foo
{ "key": "foo", "value": "hello", "type": "string", "ttl_remaining": 58 }

// PATCH /keys/count/integer/incr
{ "delta": 5 }
```

### Error codes

| Exception | HTTP |
|-----------|------|
| `KeyNotFound` | 404 |
| `TypeMismatch` | 409 |
| `CapacityError` | 507 |

---

## Taskfile

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

---

## Testing Strategy

**`tests/conftest.py`**: fixtures providing a `MemoryStore` with small capacity (e.g., `max_keys=3`, `initial_capacity=2`) and a FastAPI `TestClient` with that store injected via DI override.

**`tests/test_store.py`** (unit — no FastAPI):
- Set/get each value type
- TTL expiry (mock `time.time`)
- LRU eviction at `max_keys`
- Dynamic grow beyond `initial_capacity`
- Type mismatch raises `TypeMismatch`
- Get expired key raises `KeyNotFound`

**`tests/test_api.py`** (integration — httpx TestClient):
- Full CRUD per type
- Correct HTTP status codes for all error cases
- TTL reflected in `ttl_remaining` response field
- Flush endpoint clears all keys

---

## Future Work (documented in `docs/scaling.md`)

- Background TTL sweep thread (avoids stale keys consuming slots)
- Persistence: append-only log (AOF) or periodic snapshot (RDB analogue)
- Multi-node: consistent hashing for sharding, leader-follower replication
- GKE deployment, horizontal pod autoscaling
- gRPC adapter (drop-in via `StoragePort`)
- Prometheus metrics endpoint
