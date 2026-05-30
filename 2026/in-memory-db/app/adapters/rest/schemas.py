from pydantic import BaseModel


# --- Request models ---

class StringSetRequest(BaseModel):
    value: str
    ttl: int | None = None


class IntegerSetRequest(BaseModel):
    value: int
    ttl: int | None = None


class ListSetRequest(BaseModel):
    value: list[str]
    ttl: int | None = None


class HashSetRequest(BaseModel):
    value: dict[str, str]
    ttl: int | None = None


class IncrRequest(BaseModel):
    delta: int = 1


class ListPushRequest(BaseModel):
    item: str


class HashFieldSetRequest(BaseModel):
    field: str
    value: str


class HashFieldGetRequest(BaseModel):
    field: str


class ExpireRequest(BaseModel):
    ttl: int


# --- Response models ---

class EntryResponse(BaseModel):
    key: str
    value: str | int | list[str] | dict[str, str]
    type: str
    ttl_remaining: float | None = None


class KeysResponse(BaseModel):
    keys: list[str]


class ListPopResponse(BaseModel):
    value: str


class HashFieldResponse(BaseModel):
    field: str
    value: str
