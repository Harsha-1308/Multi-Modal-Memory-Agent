import pytest


def test_path_traversal_prevention(test_env):
    storage = test_env["file_storage"]

    # Attempt path traversal on resolve_path
    with pytest.raises(ValueError):
        storage.resolve_path("../../etc/passwd")

    with pytest.raises(ValueError):
        storage.resolve_path("..\\..\\windows\\system32")

    # Attempt cross project access
    with pytest.raises(ValueError):
        storage.store_evidence_file(
            project_id="../../bad_project",
            evidence_id="ev-123",
            file_bytes=b"test",
        )


def test_nonexistent_evidence_404(client):
    res = client.get("/api/v1/evidence/non-existent-id")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "EVIDENCE_NOT_FOUND"

    res_content = client.get("/api/v1/evidence/non-existent-id/content")
    assert res_content.status_code == 404
    assert res_content.json()["error"]["code"] == "EVIDENCE_NOT_FOUND"
