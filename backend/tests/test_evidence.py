import io
import hashlib


def test_upload_and_serve_evidence(client):
    proj = client.post("/api/v1/projects", json={"name": "Evidence Project"}).json()
    chat = client.post(f"/api/v1/projects/{proj['project_id']}/chats", json={"name": "Evidence Chat"}).json()
    cid = chat["chat_id"]

    sample_content = b"console.log('Error in React render: element undefined');"
    expected_sha256 = hashlib.sha256(sample_content).hexdigest()

    # Upload evidence
    res_upload = client.post(
        f"/api/v1/chats/{cid}/evidence",
        files={"file": ("error.log", io.BytesIO(sample_content), "text/plain")},
        data={"description": "Browser error log trace"},
    )
    assert res_upload.status_code == 201
    ev_data = res_upload.json()
    eid = ev_data["evidence_id"]
    assert ev_data["sha256"] == expected_sha256
    assert ev_data["size_bytes"] == len(sample_content)
    assert ev_data["user_description"] == "Browser error log trace"

    # Get metadata
    res_meta = client.get(f"/api/v1/evidence/{eid}")
    assert res_meta.status_code == 200
    assert res_meta.json()["evidence_id"] == eid

    # Get content
    res_content = client.get(f"/api/v1/evidence/{eid}/content")
    assert res_content.status_code == 200
    assert res_content.content == sample_content
