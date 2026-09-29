def test_create_and_list_chats(client):
    proj = client.post("/api/v1/projects", json={"name": "Chat Project"}).json()
    pid = proj["project_id"]

    res_c1 = client.post(f"/api/v1/projects/{pid}/chats", json={"name": "First Chat"})
    assert res_c1.status_code == 201
    c1 = res_c1.json()
    assert c1["name"] == "First Chat"
    assert c1["project_id"] == pid
    assert c1["memory_enabled"] is True

    res_c2 = client.post(f"/api/v1/projects/{pid}/chats", json={"name": "Second Chat"})
    assert res_c2.status_code == 201
    c2 = res_c2.json()

    chats = client.get(f"/api/v1/projects/{pid}/chats").json()
    assert len(chats) == 2
    assert any(c["chat_id"] == c1["chat_id"] for c in chats)
    assert any(c["chat_id"] == c2["chat_id"] for c in chats)
