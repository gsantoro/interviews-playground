from dataclasses import dataclass
from typing import Literal

ValueType = Literal["string", "integer", "list", "hash"]
Value = str | int | list[str] | dict[str, str]


@dataclass
class Entry:
    value: Value
    value_type: ValueType
    expires_at: float | None = None  # Unix timestamp; None = no expiry
