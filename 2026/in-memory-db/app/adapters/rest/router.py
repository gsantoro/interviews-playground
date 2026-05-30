import time

from fastapi import APIRouter, Depends, Response

from app.adapters.rest.schemas import EntryResponse, KeysResponse, StringSetRequest
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


@router.post("/keys/{key}/string", response_model=EntryResponse)
def set_string(key: str, body: StringSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "string", ttl=body.ttl)
    return _entry_response(key, store)
