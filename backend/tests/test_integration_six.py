import hashlib
import io
import json
from pathlib import Path


def test_1_project_creation_creates_isolated_hindsight_banks_and_supports_zero_seeds(
    client, test_env
):
    seeded = client.post(
        "/api/v1/projects",
        json={
            "name": "Payment Project",
            "project_type": "code",
            "description": "Payment service",
            "seed_memories": [
                {"text": "Payment service uses Redis for caching."},
                {"text": "PostgreSQL stores wallet data."},
            ],
        },
    )
    empty = client.post(
        "/api/v1/projects",
        json={
            "name": "Legal Project",
            "project_type": "legal",
            "description": "Contract review",
        },
    )

    assert seeded.status_code == 201
    assert empty.status_code == 201

    project_a = seeded.json()
    project_b = empty.json()

    assert project_a["hindsight_bank_id"] == f"bank-{project_a['project_id']}"
    assert project_b["hindsight_bank_id"] == f"bank-{project_b['project_id']}"
    assert project_a["hindsight_bank_id"] != project_b["hindsight_bank_id"]

    assert list(test_env["fake_memory"].banks) == [
        project_a["hindsight_bank_id"],
        project_b["hindsight_bank_id"],
    ]

    memories_a = client.get(
        f"/api/v1/projects/{project_a['project_id']}/memories"
    ).json()
    memories_b = client.get(
        f"/api/v1/projects/{project_b['project_id']}/memories"
    ).json()

    assert len(memories_a) == 2
    assert len(memories_b) == 0


def test_2_multiple_chats_share_project_bank_and_memory_is_project_isolated(
    client, test_env
):
    project_a = client.post(
        "/api/v1/projects",
        json={
            "name": "Alpha",
            "seed_memories": [{"text": "Alpha unique memory ORBIT-742."}],
        },
    ).json()
    project_b = client.post(
        "/api/v1/projects",
        json={
            "name": "Beta",
            "seed_memories": [{"text": "Beta unique memory NEBULA-311."}],
        },
    ).json()

    chat_a1 = client.post(
        f"/api/v1/projects/{project_a['project_id']}/chats",
        json={"name": "Alpha Chat 1"},
    ).json()
    chat_a2 = client.post(
        f"/api/v1/projects/{project_a['project_id']}/chats",
        json={"name": "Alpha Chat 2"},
    ).json()
    chat_b = client.post(
        f"/api/v1/projects/{project_b['project_id']}/chats",
        json={"name": "Beta Chat"},
    ).json()

    assert chat_a1["project_id"] == project_a["project_id"]
    assert chat_a2["project_id"] == project_a["project_id"]
    assert chat_a1["memory_enabled"] is True
    assert chat_a2["memory_enabled"] is True

    project_a_chats = client.get(
        f"/api/v1/projects/{project_a['project_id']}/chats"
    ).json()
    assert {c["chat_id"] for c in project_a_chats} == {
        chat_a1["chat_id"],
        chat_a2["chat_id"],
    }

    assert test_env["fake_memory"].banks[project_a["hindsight_bank_id"]]
    assert test_env["fake_memory"].banks[project_b["hindsight_bank_id"]]
    assert project_a["hindsight_bank_id"] != project_b["hindsight_bank_id"]

    # Verify the actual runtime would read from the selected project's bank.
    client.post(
        f"/api/v1/chats/{chat_a1['chat_id']}/messages",
        data={"content": "what memory is recorded in this project?"},
    )
    recall_calls = [
        call for call in test_env["fake_memory"].calls if call[0] == "recall"
    ]
    assert any(call[1] == project_a["hindsight_bank_id"] for call in recall_calls)
    assert all(
        call[1] != project_b["hindsight_bank_id"]
        for call in recall_calls
        if call[2] and "this project" in call[2]
    )


def test_3_memory_on_http_response_contains_agent_answer_and_runtime_metrics(
    client
):
    project = client.post(
        "/api/v1/projects",
        json={
            "name": "Payment",
            "seed_memories": [
                {"text": "The payment service uses Redis for caching."}
            ],
        },
    ).json()
    chat = client.post(
        f"/api/v1/projects/{project['project_id']}/chats",
        json={"name": "Debugging"},
    ).json()

    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={
            "content": "What does the payment service use in this project?"
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["message"]["role"] == "assistant"
    assert payload["message"]["content"]
    assert payload["memory"]["enabled"] is True
    assert payload["memory"]["mode"] == "memory"
    assert payload["user_message_id"]

    metrics = payload["evidence"]["metrics"]
    assert metrics["retrieval_similarity"] == 0.91
    assert metrics["c6_multiplier"] == 1.0
    assert "learning_confidence" in metrics
    assert "evidence_coverage" in metrics

    messages = client.get(
        f"/api/v1/chats/{chat['chat_id']}/messages"
    ).json()
    assistant = [m for m in messages if m["role"] == "assistant"][-1]
    assert assistant["content"] == payload["message"]["content"]
    assert assistant["metadata"]["evidence"]["source_evidence"]


def test_4_uploaded_evidence_is_stored_analyzed_linked_and_retained_in_hindsight(
    client, test_env
):
    project = client.post(
        "/api/v1/projects",
        json={"name": "Evidence Project", "project_type": "code"},
    ).json()
    chat = client.post(
        f"/api/v1/projects/{project['project_id']}/chats",
        json={"name": "Evidence Chat"},
    ).json()

    file_bytes = b"fake-image-bytes-for-deterministic-test"
    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={
            "content": "Please remember this architecture.",
            "attachment_descriptions": json.dumps(
                [{"index": 0, "description": "This is the payment architecture."}]
            ),
        },
        files={
            "files": ("architecture.png", io.BytesIO(file_bytes), "image/png")
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["message"]["role"] == "assistant"
    assert payload["evidence"]["source_evidence"]

    source = payload["evidence"]["source_evidence"][0]
    assert source["source_type"] == "uploaded_evidence"
    assert source["original_filename"] == "architecture.png"
    assert source["user_description"] == "This is the payment architecture."
    assert source["semantic_description"]
    assert source["combined_understanding"]
    assert source["canonical_memory_id"] is not None
    assert source["hindsight_memory"]["canonical_memory_id"] == source[
        "canonical_memory_id"
    ]

    evidence_rows = test_env["evidence_repo"].list_for_chat(chat["chat_id"])
    assert len(evidence_rows) == 1
    evidence = evidence_rows[0]
    assert evidence["message_id"] == payload["user_message_id"]
    assert evidence["canonical_memory_id"] is not None

    stored_path = Path(test_env["file_storage"].root_path) / evidence["storage_key"]
    assert stored_path.exists()
    assert stored_path.read_bytes() == file_bytes
    assert evidence["sha256"] == hashlib.sha256(file_bytes).hexdigest()

    retained = [
        call
        for call in test_env["fake_memory"].calls
        if call[0] == "retain"
    ]
    assert any(
        evidence["evidence_id"] in call[2]
        and "payment architecture" in call[2].lower()
        for call in retained
    )


def test_5_memory_off_uses_evidence_but_never_touches_hindsight(
    client, test_env
):
    project = client.post(
        "/api/v1/projects",
        json={"name": "Memory Off Project"},
    ).json()
    chat = client.post(
        f"/api/v1/projects/{project['project_id']}/chats",
        json={"name": "No Memory Chat"},
    ).json()

    client.patch(
        f"/api/v1/chats/{chat['chat_id']}/settings",
        json={"memory_enabled": False},
    )

    test_env["fake_memory"].calls.clear()

    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={
            "content": "What do you see here?",
            "attachment_descriptions": json.dumps(
                [{"index": 0, "description": "This is a payment architecture."}]
            ),
        },
        files={
            "files": ("diagram.png", io.BytesIO(b"image-bytes"), "image/png")
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["memory"]["enabled"] is False
    assert payload["memory"]["status"] == "disabled"
    assert payload["evidence"]["source_evidence"][0]["hindsight_memory"] is None
    assert payload["evidence"]["source_evidence"][0]["canonical_memory_id"] is None

    memory_calls = test_env["fake_memory"].calls
    assert not [c for c in memory_calls if c[0] in {"recall", "retain"}]


def test_6_response_trace_and_evidence_survive_refresh_via_get_messages(
    client, test_env
):
    project = client.post(
        "/api/v1/projects",
        json={"name": "Persistence Project"},
    ).json()
    chat = client.post(
        f"/api/v1/projects/{project['project_id']}/chats",
        json={"name": "Persistent Chat"},
    ).json()

    response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/messages",
        data={
            "content": "Remember this image for later.",
            "attachment_descriptions": json.dumps(
                [{"index": 0, "description": "Architecture for the payment system."}]
            ),
        },
        files={
            "files": ("arch.png", io.BytesIO(b"persistent-image"), "image/png")
        },
    )
    assert response.status_code == 200
    payload = response.json()

    messages = client.get(
        f"/api/v1/chats/{chat['chat_id']}/messages"
    )
    assert messages.status_code == 200
    stored_messages = messages.json()

    user = [m for m in stored_messages if m["message_id"] == payload["user_message_id"]][0]
    assistant = [
        m for m in stored_messages if m["message_id"] == payload["message"]["message_id"]
    ][0]

    assert user["metadata"]["attachments_count"] == 1
    assert assistant["metadata"]["evidence"]["source_evidence"]
    assert assistant["metadata"]["evidence"]["source_evidence"][0]["evidence_id"]

    evidence_id = assistant["metadata"]["evidence"]["source_evidence"][0]["evidence_id"]
    evidence = client.get(f"/api/v1/evidence/{evidence_id}").json()
    assert evidence["message_id"] == payload["user_message_id"]
    assert evidence["original_filename"] == "arch.png"
    assert evidence["canonical_memory_id"] is not None

    content = client.get(f"/api/v1/evidence/{evidence_id}/content")
    assert content.status_code == 200
    assert content.content == b"persistent-image"


def test_7_standalone_evidence_endpoint_respects_memory_toggle(client, test_env):
    project = client.post(
        "/api/v1/projects",
        json={"name": "Standalone Evidence Project", "project_type": "research"},
    ).json()
    chat = client.post(
        f"/api/v1/projects/{project['project_id']}/chats",
        json={"name": "Evidence Upload Chat"},
    ).json()

    test_env["fake_memory"].calls.clear()
    on_response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/evidence",
        data={"description": "This diagram documents the payment architecture."},
        files={
            "file": ("payment.png", io.BytesIO(b"standalone-image"), "image/png")
        },
    )
    assert on_response.status_code == 201
    on_payload = on_response.json()
    assert on_payload["canonical_memory_id"] is not None
    assert any(
        call[0] == "retain" and on_payload["evidence_id"] in call[2]
        for call in test_env["fake_memory"].calls
    )

    client.patch(
        f"/api/v1/chats/{chat['chat_id']}/settings",
        json={"memory_enabled": False},
    )
    test_env["fake_memory"].calls.clear()

    off_response = client.post(
        f"/api/v1/chats/{chat['chat_id']}/evidence",
        data={"description": "This should remain session evidence only."},
        files={
            "file": ("offline.png", io.BytesIO(b"offline-image"), "image/png")
        },
    )
    assert off_response.status_code == 201
    off_payload = off_response.json()
    assert off_payload["canonical_memory_id"] is None
    assert not [
        call for call in test_env["fake_memory"].calls
        if call[0] in {"retain", "recall"}
    ]
