"""Real-provider smoke test for the FastAPI -> Hindsight -> Groq path.

Run from the backend directory with real credentials available in .env or the
process environment:

    python scripts/live_backend_smoke.py

This script intentionally lives outside pytest so the deterministic test
fixtures cannot replace the real Hindsight/Groq SDKs.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path


def main() -> int:
    if not os.getenv("HINDSIGHT_API_KEY") or not os.getenv("GROQ_API_KEY"):
        print(
            "LIVE SMOKE NOT RUN: set HINDSIGHT_API_KEY and GROQ_API_KEY "
            "(for example in backend/.env) before running this script."
        )
        return 0

    temp_dir = Path(tempfile.mkdtemp(prefix="project_memory_live_smoke_"))
    db_path = temp_dir / "project.db"
    storage_root = temp_dir / "storage"
    data_dir = temp_dir / "memory_data"
    storage_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # These must be set before importing the FastAPI dependency graph so the
    # global application DB points at this disposable smoke-test directory.
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["STORAGE_ROOT"] = str(storage_root)

    # Imports are intentionally delayed until credentials/temp paths are ready.
    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.api import deps
    from app.db import AppDatabase
    from app.repositories.chat_repository import ChatRepository
    from app.repositories.evidence_repository import EvidenceRepository
    from app.repositories.message_repository import MessageRepository
    from app.repositories.project_repository import ProjectRepository
    from app.services.canonical_memory_service import CanonicalMemoryService
    from app.services.chat_runtime_service import ChatRuntimeService
    from app.services.chat_service import ChatService
    from app.services.evidence_understanding_service import GroqEvidenceUnderstandingService
    from app.services.file_storage_service import FileStorageService
    from app.services.learning_aware_groq_agent import LearningAwareGroqAgent
    from app.repositories.sqlite.learning_repository import SQLiteLearningRepository
    from app.services.memory_learning_state_service import MemoryLearningStateService
    from app.services.memory_service import MemoryService
    from app.services.normal_chat_service import NormalChatService
    from app.services.project_memory_runtime import ProjectMemoryRuntime
    from app.services.project_service import ProjectService

    db = AppDatabase(str(db_path))
    project_repo = ProjectRepository(database=db)
    chat_repo = ChatRepository(database=db)
    message_repo = MessageRepository(database=db)
    evidence_repo = EvidenceRepository(database=db)
    file_storage = FileStorageService(root_dir=str(storage_root))
    memory_service = MemoryService()
    canonical_path = data_dir / "memory_registry.db"
    project_service = ProjectService(
        project_repo=project_repo,
        memory_service=memory_service,
        canonical_db_path=str(canonical_path),
        learning_data_dir=str(data_dir),
    )
    chat_service = ChatService(chat_repo=chat_repo, project_repo=project_repo)
    normal_chat = NormalChatService()
    evidence_understanding = GroqEvidenceUnderstandingService()
    groq_agent = LearningAwareGroqAgent()

    def runtime_factory(**kwargs):
        project_id = kwargs["project_id"]
        return ProjectMemoryRuntime(
            **kwargs,
            message_repo=message_repo,
            evidence_repo=evidence_repo,
            db_dir=str(data_dir),
            memory_service=memory_service,
            canonical_memory_service=CanonicalMemoryService(db_path=str(canonical_path)),
            learning_repository=SQLiteLearningRepository(
                db_path=str(data_dir / f"learning_{project_id}.db")
            ),
            groq_agent=groq_agent,
        )

    chat_runtime = ChatRuntimeService(
        project_repo=project_repo,
        chat_repo=chat_repo,
        message_repo=message_repo,
        evidence_repo=evidence_repo,
        normal_chat=normal_chat,
        memory_runtime_factory=runtime_factory,
    )

    # Inject the real providers into the same API dependency slots used by the
    # browser, but backed by a disposable local SQLite database.
    deps._project_repo = project_repo
    deps._chat_repo = chat_repo
    deps._message_repo = message_repo
    deps._evidence_repo = evidence_repo
    deps._file_storage = file_storage
    deps._evidence_understanding = evidence_understanding
    deps._project_service = project_service
    deps._chat_service = chat_service
    deps._chat_runtime_service = chat_runtime

    created_banks = []
    try:
        marker_a = "LIVE-ORBIT-A-742"
        marker_b = "LIVE-NEBULA-B-311"

        with TestClient(app) as client:
            health = client.get("/api/v1/health")
            assert health.status_code == 200, health.text
            print("[PASS] GET /api/v1/health")

            project_a_response = client.post(
                "/api/v1/projects",
                json={
                    "name": "Live Project A",
                    "project_type": "code",
                    "description": "Real-provider smoke project A",
                    "seed_memories": [
                        {"text": f"Project A marker is {marker_a}."}
                    ],
                },
            )
            assert project_a_response.status_code == 201, project_a_response.text
            project_a = project_a_response.json()

            project_b_response = client.post(
                "/api/v1/projects",
                json={
                    "name": "Live Project B",
                    "project_type": "research",
                    "description": "Real-provider smoke project B",
                    "seed_memories": [
                        {"text": f"Project B marker is {marker_b}."}
                    ],
                },
            )
            assert project_b_response.status_code == 201, project_b_response.text
            project_b = project_b_response.json()

            bank_a = project_a["hindsight_bank_id"]
            bank_b = project_b["hindsight_bank_id"]
            created_banks.extend([bank_a, bank_b])
            assert bank_a != bank_b
            print("[PASS] two projects created with distinct Hindsight banks")

            # Direct real SDK verification of bank existence.
            memory_service.hindsight.client.get_bank_config(bank_a)
            memory_service.hindsight.client.get_bank_config(bank_b)
            print("[PASS] both Hindsight banks exist in the real provider")

            chats_a = []
            for name in ("Live A Chat 1", "Live A Chat 2"):
                response = client.post(
                    f"/api/v1/projects/{project_a['project_id']}/chats",
                    json={"name": name},
                )
                assert response.status_code == 201, response.text
                chats_a.append(response.json())

            assert chats_a[0]["project_id"] == project_a["project_id"]
            assert chats_a[1]["project_id"] == project_a["project_id"]
            print("[PASS] multiple chats share one project")

            # Real Hindsight isolation check.
            recalled_a = memory_service.recall(bank_a, marker_a)
            recalled_b = memory_service.recall(bank_b, marker_a)
            texts_a = [str(x.get("text", "")) for x in recalled_a.get("results", [])]
            texts_b = [str(x.get("text", "")) for x in recalled_b.get("results", [])]
            assert any(marker_a in text for text in texts_a), texts_a
            assert not any(marker_a in text for text in texts_b), texts_b
            print("[PASS] Hindsight recall is project-isolated")

            # Prove the browser-facing POST reaches the real memory runtime and
            # returns the assistant answer plus its memory envelope.
            message_response = client.post(
                f"/api/v1/chats/{chats_a[0]['chat_id']}/messages",
                data={
                    "content": "What marker did I store for this project?",
                },
            )
            assert message_response.status_code == 200, message_response.text
            payload = message_response.json()
            assert payload["memory"]["enabled"] is True
            assert payload["message"]["role"] == "assistant"
            assert payload["message"]["content"].strip()
            assert "evidence" in payload
            assert "metrics" in payload["evidence"]
            print("[PASS] real FastAPI POST -> Hindsight/C1-C6 -> Groq -> JSON response")
            print("       assistant:", payload["message"]["content"].replace("\n", " ")[:220])

        print("\nREAL PROVIDER SMOKE PASSED")
        return 0
    except Exception as exc:
        print("\nREAL PROVIDER SMOKE FAILED:", exc, file=sys.stderr)
        return 1
    finally:
        for bank_id in created_banks:
            try:
                memory_service.hindsight.client.delete_bank(bank_id)
            except Exception:
                pass
        try:
            memory_service.close()
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
