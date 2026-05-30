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
