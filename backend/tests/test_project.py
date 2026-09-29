def test_create_project(client):
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "Wallet Concurrency",
            "project_type": "code",
            "description": "Fixing double-spend issues",
            "seed_memories": [{"text": "Pessimistic locking was implemented."}],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Wallet Concurrency"
    assert data["project_type"] == "code"
    assert data["project_id"].startswith("proj-")
    assert data["hindsight_bank_id"] == f"bank-{data['project_id']}"


def test_create_project_zero_seeds(client):
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "Zero Seed Project",
            "project_type": "research",
            "description": "No seeds provided",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Zero Seed Project"


def test_list_and_get_projects(client):
    res1 = client.post("/api/v1/projects", json={"name": "Project A"})
    assert res1.status_code == 201
    pid = res1.json()["project_id"]

    res_list = client.get("/api/v1/projects")
    assert res_list.status_code == 200
    assert any(p["project_id"] == pid for p in res_list.json())

    res_get = client.get(f"/api/v1/projects/{pid}")
    assert res_get.status_code == 200
    assert res_get.json()["project_id"] == pid
