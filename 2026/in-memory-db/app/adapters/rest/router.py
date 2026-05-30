import time

from fastapi import APIRouter, Depends, Response

from app.adapters.rest.schemas import (
    EntryResponse,
    ExpireRequest,
    HashFieldGetRequest,
    HashFieldResponse,
    HashFieldSetRequest,
    HashSetRequest,
    IncrRequest,
    IntegerSetRequest,
    KeysResponse,
    ListPopResponse,
    ListPushRequest,
    ListSetRequest,
    StringSetRequest,
)
from app.core.exceptions import KeyNotFound, TypeMismatch
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


@router.post("/keys/{key}/integer", response_model=EntryResponse)
def set_integer(key: str, body: IntegerSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "integer", ttl=body.ttl)
    return _entry_response(key, store)


@router.post("/keys/{key}/list", response_model=EntryResponse)
def set_list(key: str, body: ListSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "list", ttl=body.ttl)
    return _entry_response(key, store)


@router.post("/keys/{key}/hash", response_model=EntryResponse)
def set_hash(key: str, body: HashSetRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.set(key, body.value, "hash", ttl=body.ttl)
    return _entry_response(key, store)


@router.patch("/keys/{key}/integer/incr", response_model=EntryResponse)
def incr_integer(key: str, body: IncrRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    entry = store.get(key)
    if entry.value_type != "integer":
        raise TypeMismatch(key, "integer", entry.value_type)
    store.update_value(key, int(entry.value) + body.delta)
    return _entry_response(key, store)


@router.patch("/keys/{key}/list/push", response_model=EntryResponse)
def list_push(key: str, body: ListPushRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    entry = store.get(key)
    if entry.value_type != "list":
        raise TypeMismatch(key, "list", entry.value_type)
    store.update_value(key, list(entry.value) + [body.item])
    return _entry_response(key, store)


@router.patch("/keys/{key}/list/pop", response_model=ListPopResponse)
def list_pop(key: str, store: StoragePort = Depends(get_store)) -> ListPopResponse:
    entry = store.get(key)
    if entry.value_type != "list":
        raise TypeMismatch(key, "list", entry.value_type)
    lst = list(entry.value)
    if not lst:
        raise KeyNotFound(key)
    item = lst.pop()
    store.update_value(key, lst)
    return ListPopResponse(value=item)


@router.patch("/keys/{key}/hash/set", response_model=EntryResponse)
def hash_field_set(
    key: str, body: HashFieldSetRequest, store: StoragePort = Depends(get_store)
) -> EntryResponse:
    entry = store.get(key)
    if entry.value_type != "hash":
        raise TypeMismatch(key, "hash", entry.value_type)
    updated = dict(entry.value) | {body.field: body.value}
    store.update_value(key, updated)
    return _entry_response(key, store)


@router.patch("/keys/{key}/hash/get", response_model=HashFieldResponse)
def hash_field_get(
    key: str, body: HashFieldGetRequest, store: StoragePort = Depends(get_store)
) -> HashFieldResponse:
    entry = store.get(key)
    if entry.value_type != "hash":
        raise TypeMismatch(key, "hash", entry.value_type)
    h = dict(entry.value)
    if body.field not in h:
        raise KeyNotFound(body.field)
    return HashFieldResponse(field=body.field, value=h[body.field])


@router.patch("/keys/{key}/expire", response_model=EntryResponse)
def expire_key(key: str, body: ExpireRequest, store: StoragePort = Depends(get_store)) -> EntryResponse:
    store.expire(key, body.ttl)
    return _entry_response(key, store)
