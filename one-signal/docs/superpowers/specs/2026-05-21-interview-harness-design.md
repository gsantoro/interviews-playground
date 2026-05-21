# Interview Harness — Redis Clone (Python/uv)

**Date:** 2026-05-21
**Context:** Live coding interview scaffold. Candidate clones, runs the app, implements Redis clone features from scratch. This repo is the harness only — no Redis logic.

---

## Goal

Minimal FastAPI REST API shell. Proves the stack works. Shows candidates the code patterns to follow. Gets out of their way.

---

## Structure

```
one-signal/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app instance, mounts routers
│   └── routers/
│       ├── __init__.py
│       ├── health.py    # GET /health
│       └── hello.py     # GET /hello
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # TestClient fixture
│   ├── test_health.py
│   └── test_hello.py
├── pyproject.toml       # uv project config
└── Taskfile.yml         # run / test / lint tasks
```

---

## Endpoints

| Method | Path | Response | Body |
|--------|------|----------|------|
| GET | `/health` | 200 | `{"status": "ok"}` |
| GET | `/hello` | 200 | `{"message": "Hello, World!"}` |

Both return typed Pydantic response models with full type annotations.

---

## Dependencies

**Runtime:** `fastapi`, `uvicorn[standard]`
**Dev:** `pytest`, `httpx`, `ruff`

Managed via `uv`. No virtualenv manual setup needed.

---

## Tests

`conftest.py` — `client` fixture using FastAPI `TestClient` (sync).

One test per endpoint:
- `test_health.py`: `GET /health` → assert `200`, body `{"status": "ok"}`
- `test_hello.py`: `GET /hello` → assert `200`, body `{"message": "Hello, World!"}`

No async test setup required. Pattern is intentionally simple so candidates can extend it.

---

## Taskfile Tasks

| Task | Command |
|------|---------|
| `task run` | `uv run uvicorn app.main:app --reload` |
| `task test` | `uv run pytest -v` |
| `task lint` | `uv run ruff check .` |

Taskfile replaces README for day-to-day commands.

---

## Design Decisions

- **uv** over pip/poetry: faster, lockfile included, single tool for venv + deps
- **Taskfile** over Makefile/README: self-documenting, no make syntax quirks
- **Sync TestClient** over async pytest-asyncio: simpler, sufficient for HTTP endpoint tests
- **Ruff** over flake8/pylint: zero-config, fast, good interview default
- **Pydantic response models** on both endpoints: shows candidates the typing pattern
- **No Redis code**: harness is a shell, all implementation is candidate's work
