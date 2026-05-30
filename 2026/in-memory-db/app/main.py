from fastapi import FastAPI

from app.adapters.rest.errors import register_error_handlers
from app.adapters.rest.router import get_store, router
from app.config import ServerSettings, StoreSettings
from app.core.store import MemoryStore
from app.ports.storage import StoragePort


def create_app(store: StoragePort | None = None) -> FastAPI:
    app = FastAPI(title="in-memory-db")

    if store is None:
        cfg = StoreSettings.from_toml()
        store = MemoryStore(
            initial_capacity=cfg.initial_capacity,
            max_keys=cfg.max_keys,
            default_ttl=cfg.default_ttl_seconds,
        )

    app.dependency_overrides[get_store] = lambda: store
    app.include_router(router)
    register_error_handlers(app)

    return app


app = create_app()


def main() -> None:
    """Run the server on the configured host/port (PYREDIS_* env > config.toml)."""
    import uvicorn

    cfg = ServerSettings.from_toml_and_env()
    uvicorn.run("app.main:app", host=cfg.host, port=cfg.port, reload=True)


if __name__ == "__main__":
    main()
