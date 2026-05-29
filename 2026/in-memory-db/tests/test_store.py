import pytest
from app.core.models import Entry, ValueType, Value
from app.core.exceptions import KeyNotFound, TypeMismatch, CapacityError
from app.ports.storage import StoragePort
from app.core.store import MemoryStore


def test_imports() -> None:
    assert Entry is not None
    assert ValueType is not None
    assert Value is not None
    assert KeyNotFound is not None
    assert TypeMismatch is not None
    assert CapacityError is not None
    assert StoragePort is not None


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(initial_capacity=5, max_keys=5, default_ttl=0)


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
