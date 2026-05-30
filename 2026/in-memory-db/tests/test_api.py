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
