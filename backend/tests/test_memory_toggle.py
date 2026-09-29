def test_memory_toggle_settings_and_response(client):
    proj = client.post("/api/v1/projects", json={"name": "Toggle Project"}).json()
    chat = client.post(f"/api/v1/projects/{proj['project_id']}/chats", json={"name": "Toggle Chat"}).json()
    cid = chat["chat_id"]
    assert chat["memory_enabled"] is True

    # 1. Turn Memory OFF
    res_off = client.patch(f"/api/v1/chats/{cid}/settings", json={"memory_enabled": False})
    assert res_off.status_code == 200
    assert res_off.json()["memory_enabled"] is False

    # 2. Send message in Memory OFF mode
    res_msg_off = client.post(
        f"/api/v1/chats/{cid}/messages",
        data={"content": "What is Python?"},
    )
    assert res_msg_off.status_code == 200
    data_off = res_msg_off.json()
    assert data_off["memory"]["enabled"] is False
    assert data_off["memory"]["status"] == "disabled"
    assert data_off["memory"]["mode"] == "general"

    # 3. Turn Memory back ON
    res_on = client.patch(f"/api/v1/chats/{cid}/settings", json={"memory_enabled": True})
    assert res_on.status_code == 200
    assert res_on.json()["memory_enabled"] is True
