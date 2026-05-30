from app.config import ServerSettings, StoreSettings


def test_store_settings_from_toml() -> None:
    s = StoreSettings.from_toml()
    assert s.initial_capacity == 1000
    assert s.max_keys == 10000
    assert s.default_ttl_seconds == 0


def test_server_settings_from_toml_defaults(monkeypatch) -> None:
    # Clear any PYREDIS_* leaking from the shell (.envrc) so we test TOML values.
    monkeypatch.delenv("PYREDIS_HOST", raising=False)
    monkeypatch.delenv("PYREDIS_PORT", raising=False)
    srv = ServerSettings.from_toml_and_env()
    assert srv.host == "0.0.0.0"
    assert srv.port == 8000


def test_env_var_overrides_toml(monkeypatch) -> None:
    monkeypatch.setenv("PYREDIS_HOST", "127.0.0.1")
    monkeypatch.setenv("PYREDIS_PORT", "9999")
    srv = ServerSettings.from_toml_and_env()
    assert srv.host == "127.0.0.1"
    assert srv.port == 9999


def test_env_var_partial_override(monkeypatch) -> None:
    # Only host overridden; port falls back to config.toml.
    monkeypatch.setenv("PYREDIS_HOST", "10.0.0.1")
    monkeypatch.delenv("PYREDIS_PORT", raising=False)
    srv = ServerSettings.from_toml_and_env()
    assert srv.host == "10.0.0.1"
    assert srv.port == 8000
