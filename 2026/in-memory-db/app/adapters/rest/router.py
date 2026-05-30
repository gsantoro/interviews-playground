from fastapi import APIRouter, Depends  # noqa: F401 — Depends used by route handlers in later tasks
from app.ports.storage import StoragePort


router = APIRouter()


def get_store() -> StoragePort:
    raise NotImplementedError("get_store dependency must be overridden")
