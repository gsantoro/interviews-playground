from app.core.models import Entry
from app.ports.storage import StoragePort


def test_imports() -> None:
    assert Entry is not None
    assert StoragePort is not None
