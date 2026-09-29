def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "app_name" in data


def test_standardized_error_format(client):
    res = client.get("/api/v1/projects/non-existent-proj-id")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert data["error"]["code"] == "PROJECT_NOT_FOUND"


def test_chat_not_found(client):
    res = client.get("/api/v1/chats/non-existent-chat-id")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "CHAT_NOT_FOUND"
