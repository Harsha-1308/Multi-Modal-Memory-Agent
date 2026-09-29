import io
import json


def _create_project_and_chat(client, name="Regression Project", seeds=None):
    project = client.post(
        "/api/v1/projects",
        json={"name": name, "seed_memories": seeds or []},
    ).json()
    chat = client.post(
        f"/api/v1/projects/{project['project_id']}/chats",
        json={"name": "Regression Chat"},
    ).json()
    return project, chat


def test_history_query_recalls_short_recent_update(client):
    project, chat = _create_project_and_chat(client)

    first = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={"content": "my frontend got crashed"},
    )
    assert first.status_code == 200
    assert first.json()["memory"]["enabled"] is True
    assert first.json()["message"]["content"]

    second = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={"content": "what was my problem before"},
    )
    assert second.status_code == 200
    payload = second.json()

    assert payload["memory"]["enabled"] is True
    assert "sufficiently supported" not in payload["message"]["content"]
    texts = [item.get("text", "") for item in payload["evidence"]["source_evidence"]]
    assert any("frontend got crashed" in text for text in texts)
    assert payload["evidence"]["metrics"].get("retrieval_similarity") == 0.91


def test_memory_inventory_is_project_query_and_lists_verified_records(client):
    seed = "The payment service uses Redis for caching."
    project, chat = _create_project_and_chat(client, seeds=[{"text": seed}])

    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={"content": "what do you have in your memory"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["memory"]["enabled"] is True
    assert payload["evidence"]["understanding"]["mode"] == "MEMORY_INVENTORY"
    assert any(seed in item.get("text", "") for item in payload["evidence"]["source_evidence"])
    assert "project memories" in payload["message"]["content"]


def test_general_question_can_use_related_project_memory_without_becoming_project_query(client):
    seed = "The project includes a monarch butterfly image identified by the user."
    project, chat = _create_project_and_chat(client, seeds=[{"text": seed}])

    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={"content": "what do you know about butterflies"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["memory"]["enabled"] is True
    assert payload["evidence"]["understanding"]["intent"] == "GENERAL_QUERY"
    assert payload["evidence"]["understanding"]["memory_match"] is True
    assert "monarch butterfly" in payload["message"]["content"].lower()


def test_learning_state_is_not_dropped_by_message_response_schema(client):
    project, chat = _create_project_and_chat(
        client,
        seeds=[{"text": "The service uses pessimistic database locking."}],
    )
    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={"content": "what locking approach does this project use"},
    )
    assert response.status_code == 200
    evidence = response.json()["evidence"]
    assert "learning_state" in evidence


def test_uploaded_evidence_has_one_backend_source_and_one_attachment(client):
    project, chat = _create_project_and_chat(client)
    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={
            "content": "this is the architecture screenshot",
            "attachment_descriptions": json.dumps(
                [{"index": 0, "description": "Payment architecture diagram."}]
            ),
        },
        files={"files": ("arch.png", io.BytesIO(b"image-bytes"), "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    sources = [s for s in payload["evidence"]["source_evidence"] if s.get("evidence_id")]
    attachments = [a for a in payload["attachments"] if a.get("evidence_id")]
    assert len(sources) == 1
    assert len(attachments) == 1
    assert sources[0]["evidence_id"] == attachments[0]["evidence_id"]


def test_empty_message_is_rejected_but_evidence_only_message_is_allowed(client):
    project, chat = _create_project_and_chat(client)
    empty = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={"content": ""},
    )
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "EMPTY_MESSAGE"

    evidence_only = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={
            "content": "",
            "attachment_descriptions": json.dumps(
                [{"index": 0, "description": "A payment architecture diagram."}]
            ),
        },
        files={"files": ("only.png", io.BytesIO(b"only-image"), "image/png")},
    )
    assert evidence_only.status_code == 200
    assert evidence_only.json()["attachments"]
