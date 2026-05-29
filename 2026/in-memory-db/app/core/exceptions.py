class KeyNotFound(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Key not found: '{key}'")
        self.key = key


class TypeMismatch(Exception):
    def __init__(self, key: str, expected: str, got: str) -> None:
        super().__init__(f"Key '{key}' holds type '{got}', not '{expected}'")


class CapacityError(Exception):
    pass
