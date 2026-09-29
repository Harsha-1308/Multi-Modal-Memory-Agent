def test_project_memory_and_chat_isolation(client, test_env):
    # 1. Create Project A
    res_a = client.post(
        "/api/v1/projects",
        json={
            "name": "Project Alpha",
            "seed_memories": [{"text": "Alpha confidential fact 123"}],
        },
    )
    assert res_a.status_code == 201
    pid_a = res_a.json()["project_id"]

    # 2. Create Project B
    res_b = client.post(
        "/api/v1/projects",
        json={
            "name": "Project Beta",
            "seed_memories": [{"text": "Beta public fact 456"}],
        },
    )
    assert res_b.status_code == 201
    pid_b = res_b.json()["project_id"]

    # 3. Create chat in A and chat in B
    chat_a = client.post(f"/api/v1/projects/{pid_a}/chats", json={"name": "Chat A"}).json()
    chat_b = client.post(f"/api/v1/projects/{pid_b}/chats", json={"name": "Chat B"}).json()

    # 4. Post message to chat A
    test_env["message_repo"].create(
        chat_id=chat_a["chat_id"],
        role="user",
        content="Secret message in Alpha",
        message_type="CHAT",
    )

    # 5. Verify Project B history does not contain Chat A's message
    history_b = client.get(f"/api/v1/projects/{pid_b}/history").json()
    assert all("Secret message in Alpha" not in m["content"] for m in history_b)

    # 6. Verify Chat B messages list does not contain Chat A's message
    msgs_b = client.get(f"/api/v1/chats/{chat_b['chat_id']}/messages").json()
    assert len(msgs_b) == 0

    # 7. Verify Project B memories do not contain Project A's seed memory
    mem_b = client.get(f"/api/v1/projects/{pid_b}/memories").json()
    assert all("Alpha confidential fact 123" not in m.get("text", "") for m in mem_b)
