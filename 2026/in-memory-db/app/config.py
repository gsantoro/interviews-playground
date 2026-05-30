import os
import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_toml(section: str) -> dict:
    path = Path("config.toml")
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f).get(section, {})


class StoreSettings(BaseSettings):
    initial_capacity: int = 1000
    max_keys: int = 10000
    default_ttl_seconds: int = 0

    @classmethod
    def from_toml(cls) -> "StoreSettings":
        return cls(**_load_toml("store"))


class ServerSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    model_config = SettingsConfigDict(env_prefix="PYREDIS_")

    @classmethod
    def from_toml_and_env(cls) -> "ServerSettings":
        # Precedence (highest first): PYREDIS_* env vars > config.toml > class defaults.
        # Pydantic ranks explicit init kwargs ABOVE env vars, so passing a TOML value
        # as a kwarg would shadow the env var. Drop any TOML key that the environment
        # overrides, letting pydantic-settings read it from PYREDIS_* instead.
        toml_vals = {
            key: value
            for key, value in _load_toml("server").items()
            if f"PYREDIS_{key.upper()}" not in os.environ
        }
        return cls(**toml_vals)
