from app.core.models import Entry, ValueType, Value
from app.core.exceptions import KeyNotFound, TypeMismatch, CapacityError
from app.ports.storage import StoragePort


def test_imports() -> None:
    assert Entry is not None
    assert ValueType is not None
    assert Value is not None
    assert KeyNotFound is not None
    assert TypeMismatch is not None
    assert CapacityError is not None
    assert StoragePort is not None
