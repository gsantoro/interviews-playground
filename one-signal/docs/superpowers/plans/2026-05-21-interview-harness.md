# Interview Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap a minimal FastAPI REST API shell for a live Redis clone interview — two endpoints, endpoint tests, uv project, Taskfile.

**Architecture:** Single `app/` package with a router-per-endpoint pattern. FastAPI app in `main.py` mounts routers. Tests in `tests/` use a shared `TestClient` fixture from `conftest.py`.

**Tech Stack:** Python 3.12+, uv, FastAPI, uvicorn, pytest, httpx, ruff, Taskfile (task CLI)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `pyproject.toml` | Create | uv project config, all deps |
| `Taskfile.yml` | Create | `run`, `test`, `lint` tasks |
| `app/__init__.py` | Create | Package marker |
| `app/main.py` | Create | FastAPI app instance, router mounts |
| `app/routers/__init__.py` | Create | Package marker |
| `app/routers/health.py` | Create | `GET /health` router + response model |
| `app/routers/hello.py` | Create | `GET /hello` router + response model |
| `tests/__init__.py` | Create | Package marker |
| `tests/conftest.py` | Create | `client` fixture |
| `tests/test_health.py` | Create | `GET /health` endpoint test |
| `tests/test_hello.py` | Create | `GET /hello` endpoint test |

---

## Task 1: uv Project Init

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Initialise uv project**

```bash
cd /Users/gsantoro/workspace/interviews-playground/one-signal
uv init --no-readme --python 3.12
```

Expected: `pyproject.toml` created, `.python-version` created.

- [ ] **Step 2: Add runtime dependencies**

```bash
uv add fastapi "uvicorn[standard]"
```

Expected: deps added to `pyproject.toml`, `uv.lock` generated.

- [ ] **Step 3: Add dev dependencies**

```bash
uv add --dev pytest httpx ruff
```

Expected: dev deps appear under `[dependency-groups]` in `pyproject.toml`.

- [ ] **Step 4: Verify pyproject.toml looks right**

`pyproject.toml` should contain:

```toml
[project]
name = "one-signal"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
]

[dependency-groups]
dev = [
    "httpx>=0.27.0",
    "pytest>=8.0.0",
    "ruff>=0.4.0",
]
```

Exact version pins will differ — that's fine. Confirm the dep names are present.

- [ ] **Step 5: Commit**

```bash
git init
git add pyproject.toml uv.lock .python-version
git commit -m "chore: init uv project with fastapi and dev deps"
```

---

## Task 2: Taskfile

**Files:**
- Create: `Taskfile.yml`

- [ ] **Step 1: Create Taskfile.yml**

```yaml
version: "3"

tasks:
  run:
    desc: Start the API server with hot reload
    cmd: uv run uvicorn app.main:app --reload

  test:
    desc: Run all tests
    cmd: uv run pytest -v

  lint:
    desc: Lint with ruff
    cmd: uv run ruff check .
```

- [ ] **Step 2: Verify task CLI works**

```bash
task --list
```

Expected output includes `run`, `test`, `lint` with their descriptions. If `task` is not installed: `brew install go-task`.

- [ ] **Step 3: Commit**

```bash
git add Taskfile.yml
git commit -m "chore: add Taskfile with run/test/lint tasks"
```

---

## Task 3: App Package Skeleton

**Files:**
- Create: `app/__init__.py`
- Create: `app/routers/__init__.py`
- Create: `app/main.py`

- [ ] **Step 1: Create package markers**

```bash
mkdir -p app/routers
touch app/__init__.py app/routers/__init__.py
```

- [ ] **Step 2: Create app/main.py**

```python
from fastapi import FastAPI

from app.routers import health, hello

app = FastAPI(title="one-signal")

app.include_router(health.router)
app.include_router(hello.router)
```

- [ ] **Step 3: Verify app imports cleanly**

```bash
uv run python -c "from app.main import app; print(app.title)"
```

Expected: `one-signal`

Note: this will fail until routers exist (Task 4). Come back to verify after Task 4.

- [ ] **Step 4: Commit**

```bash
git add app/
git commit -m "feat: add app package skeleton and main entry point"
```

---

## Task 4: Health Router

**Files:**
- Create: `app/routers/health.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

Create `tests/test_health.py`:

```python
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_health.py -v
```

Expected: FAIL — `ImportError` or `404` because `health` router doesn't exist yet.

- [ ] **Step 3: Implement the health router**

Create `app/routers/health.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_health.py -v
```

Expected:
```
PASSED tests/test_health.py::test_health_returns_ok
```

- [ ] **Step 5: Verify app import (from Task 3 Step 3)**

```bash
uv run python -c "from app.main import app; print(app.title)"
```

Expected: `one-signal`

- [ ] **Step 6: Commit**

```bash
git add app/routers/health.py tests/__init__.py tests/conftest.py tests/test_health.py
git commit -m "feat: add /health endpoint with test"
```

---

## Task 5: Hello Router

**Files:**
- Create: `app/routers/hello.py`
- Create: `tests/test_hello.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_hello.py`:

```python
from fastapi.testclient import TestClient


def test_hello_returns_message(client: TestClient) -> None:
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_hello.py -v
```

Expected: FAIL — `404` because `/hello` route doesn't exist yet.

- [ ] **Step 3: Implement the hello router**

Create `app/routers/hello.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel


class HelloResponse(BaseModel):
    message: str


router = APIRouter()


@router.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    return HelloResponse(message="Hello, World!")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_hello.py -v
```

Expected:
```
PASSED tests/test_hello.py::test_hello_returns_message
```

- [ ] **Step 5: Commit**

```bash
git add app/routers/hello.py tests/test_hello.py
git commit -m "feat: add /hello endpoint with test"
```

---

## Task 6: Full Suite Verification

**Files:** none new

- [ ] **Step 1: Run all tests**

```bash
task test
```

Expected:
```
PASSED tests/test_health.py::test_health_returns_ok
PASSED tests/test_hello.py::test_hello_returns_message
2 passed
```

- [ ] **Step 2: Run linter**

```bash
task lint
```

Expected: no output (zero issues). Fix any reported issues before proceeding.

- [ ] **Step 3: Smoke test the running server**

```bash
task run &
sleep 2
curl -s http://localhost:8000/health
curl -s http://localhost:8000/hello
kill %1
```

Expected:
```
{"status":"ok"}
{"message":"Hello, World!"}
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: verified full suite passes — harness ready"
```
