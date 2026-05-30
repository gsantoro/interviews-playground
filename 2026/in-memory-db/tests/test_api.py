from fastapi.testclient import TestClient


def test_list_keys_empty(client: TestClient) -> None:
    resp = client.get("/keys")
    assert resp.status_code == 200
    assert resp.json() == {"keys": []}


def test_list_keys_after_insert(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.get("/keys")
    assert "foo" in resp.json()["keys"]


def test_get_key_string(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.get("/keys/foo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "foo"
    assert data["value"] == "bar"
    assert data["type"] == "string"
    assert data["ttl_remaining"] is None


def test_get_key_with_ttl(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar", "ttl": 60})
    resp = client.get("/keys/foo")
    assert 0 < resp.json()["ttl_remaining"] <= 60


def test_get_key_not_found(client: TestClient) -> None:
    resp = client.get("/keys/missing")
    assert resp.status_code == 404


def test_delete_key(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.delete("/keys/foo")
    assert resp.status_code == 204
    assert client.get("/keys/foo").status_code == 404


def test_delete_key_not_found(client: TestClient) -> None:
    resp = client.delete("/keys/missing")
    assert resp.status_code == 404


def test_flush(client: TestClient) -> None:
    client.post("/keys/a/string", json={"value": "1"})
    client.post("/keys/b/string", json={"value": "2"})
    resp = client.delete("/keys")
    assert resp.status_code == 204
    assert client.get("/keys").json() == {"keys": []}


# --- POST set endpoints ---

def test_set_integer(client: TestClient) -> None:
    resp = client.post("/keys/count/integer", json={"value": 10})
    assert resp.status_code == 200
    assert client.get("/keys/count").json()["value"] == 10


def test_set_list(client: TestClient) -> None:
    resp = client.post("/keys/mylist/list", json={"value": ["a", "b"]})
    assert resp.status_code == 200
    assert client.get("/keys/mylist").json()["value"] == ["a", "b"]


def test_set_hash(client: TestClient) -> None:
    resp = client.post("/keys/myhash/hash", json={"value": {"name": "alice"}})
    assert resp.status_code == 200
    assert client.get("/keys/myhash").json()["value"] == {"name": "alice"}


def test_set_type_mismatch_returns_409(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.post("/keys/foo/integer", json={"value": 42})
    assert resp.status_code == 409


# --- PATCH integer/incr ---

def test_incr(client: TestClient) -> None:
    client.post("/keys/count/integer", json={"value": 10})
    resp = client.patch("/keys/count/integer/incr", json={"delta": 5})
    assert resp.status_code == 200
    assert client.get("/keys/count").json()["value"] == 15


def test_incr_default_delta(client: TestClient) -> None:
    client.post("/keys/count/integer", json={"value": 0})
    client.patch("/keys/count/integer/incr", json={})
    assert client.get("/keys/count").json()["value"] == 1


def test_incr_type_mismatch(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.patch("/keys/foo/integer/incr", json={"delta": 1})
    assert resp.status_code == 409


# --- PATCH list/push + list/pop ---

def test_list_push(client: TestClient) -> None:
    client.post("/keys/mylist/list", json={"value": ["a"]})
    client.patch("/keys/mylist/list/push", json={"item": "b"})
    assert client.get("/keys/mylist").json()["value"] == ["a", "b"]


def test_list_pop(client: TestClient) -> None:
    client.post("/keys/mylist/list", json={"value": ["a", "b"]})
    resp = client.patch("/keys/mylist/list/pop")
    assert resp.status_code == 200
    assert resp.json()["value"] == "b"
    assert client.get("/keys/mylist").json()["value"] == ["a"]


# --- PATCH hash/set + hash/get ---

def test_hash_field_set(client: TestClient) -> None:
    client.post("/keys/myhash/hash", json={"value": {}})
    client.patch("/keys/myhash/hash/set", json={"field": "name", "value": "alice"})
    assert client.get("/keys/myhash").json()["value"]["name"] == "alice"


def test_hash_field_get(client: TestClient) -> None:
    client.post("/keys/myhash/hash", json={"value": {"name": "alice"}})
    resp = client.patch("/keys/myhash/hash/get", json={"field": "name"})
    assert resp.status_code == 200
    assert resp.json()["value"] == "alice"


def test_hash_field_get_missing_field(client: TestClient) -> None:
    client.post("/keys/myhash/hash", json={"value": {}})
    resp = client.patch("/keys/myhash/hash/get", json={"field": "nope"})
    assert resp.status_code == 404


# --- PATCH expire ---

def test_expire_endpoint(client: TestClient) -> None:
    client.post("/keys/foo/string", json={"value": "bar"})
    resp = client.patch("/keys/foo/expire", json={"ttl": 60})
    assert resp.status_code == 200
    assert 0 < client.get("/keys/foo").json()["ttl_remaining"] <= 60
