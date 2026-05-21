from fastapi.testclient import TestClient


def test_hello_returns_message(client: TestClient) -> None:
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}
