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
