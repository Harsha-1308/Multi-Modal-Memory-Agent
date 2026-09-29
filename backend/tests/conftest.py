import io
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Keep the deterministic test suite runnable in a clean shell without
# requiring real provider credentials. Real-provider verification lives in
# scripts/live_backend_smoke.py and is intentionally outside pytest.
os.environ.setdefault("GROQ_API_KEY", "test")
os.environ.setdefault("HINDSIGHT_API_KEY", "test")


# The backend's production integrations require external SDKs. Tests below
# use deterministic in-process doubles so the HTTP/API contract can be tested
# without network access or credentials.
class _FakeGroqResponse:
    def __init__(self, content):
        self.choices = [
            types.SimpleNamespace(
                message=types.SimpleNamespace(content=content)
            )
        ]


class _FakeGroqCompletions:
    def create(self, *args, **kwargs):
        return _FakeGroqResponse("Test Groq response.")


class _FakeGroqChat:
    def __init__(self):
        self.completions = _FakeGroqCompletions()


class _FakeGroqSDK:
    def __init__(self, api_key=None):
        self.chat = _FakeGroqChat()


class _FakeHindsightSDK:
    def __init__(self, *args, **kwargs):
        pass

    def close(self):
        pass


sys.modules.setdefault(
    "groq",
    types.SimpleNamespace(Groq=_FakeGroqSDK),
)
sys.modules.setdefault(
    "hindsight_client",
    types.SimpleNamespace(Hindsight=_FakeHindsightSDK),
)


from app.api.main import app
from app.db import AppDatabase
from app.repositories.chat_repository import ChatRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.services.chat_runtime_service import ChatRuntimeService
from app.services.chat_service import ChatService
from app.services.evidence_understanding_service import EvidenceUnderstandingService
from app.services.file_storage_service import FileStorageService
from app.services.normal_chat_service import NormalChatService
from app.services.project_memory_runtime import ProjectMemoryRuntime
from app.services.project_service import ProjectService
from app.repositories.sqlite.learning_repository import SQLiteLearningRepository
from app.services.canonical_memory_service import CanonicalMemoryService


class FakeMemoryService:
    def __init__(self):
        self.banks = {}
        self.memories = {}
        self.calls = []

    def create_project_bank(self, bank_id, project_name, project_description):
        self.calls.append(("create_bank", bank_id))
        if bank_id in self.banks:
            raise AssertionError(f"Bank already exists: {bank_id}")
        self.banks[bank_id] = {
            "name": project_name,
            "description": project_description,
        }
        self.memories[bank_id] = []
        return {"status": "created", "bank_id": bank_id}

    def retain(self, bank_id, content):
        self.calls.append(("retain", bank_id, content))
        self.memories.setdefault(bank_id, []).append(content)
        return {"status": "retained", "bank_id": bank_id}

    def recall(self, bank_id, query, **kwargs):
        self.calls.append(("recall", bank_id, query))
        results = [
            {"text": text, "score": 0.91}
            for text in self.memories.get(bank_id, [])
        ]
        return {"results": results}

    def list_memories(self, bank_id, limit=50):
        return [
            {"id": index + 1, "text": text}
            for index, text in enumerate(self.memories.get(bank_id, [])[:limit])
        ]

    def get_bank_config(self, bank_id):
        if bank_id not in self.banks:
            raise KeyError(bank_id)
        return {"bank_id": bank_id, "config": {}}

    def close(self):
        pass


class FakeEvidenceUnderstandingService(EvidenceUnderstandingService):
    def analyze_image(self, *, file_bytes, mime_type, user_description=None):
        semantic = (
            "The image shows a payment architecture containing Redis and PostgreSQL."
        )
        if user_description:
            combined = (
                f"User description: {user_description.strip()}\n"
                f"Visual analysis: {semantic}"
            )
        else:
            combined = semantic
        return semantic, combined

    def analyze_document(
        self,
        *,
        file_bytes,
        original_filename,
        mime_type,
        user_description=None,
    ):
        semantic = (
            f"The document {original_filename} contains a recorded payment-system configuration."
        )
        if user_description:
            combined = (
                f"User description: {user_description.strip()}\n"
                f"Document analysis: {semantic}"
            )
        else:
            combined = semantic
        return semantic, combined

    def process_evidence(
        self,
        *,
        file_bytes,
        original_filename,
        mime_type,
        user_description=None,
    ):
        if mime_type.startswith("image/"):
            kind = "image"
            semantic, combined = self.analyze_image(
                file_bytes=file_bytes,
                mime_type=mime_type,
                user_description=user_description,
            )
        else:
            kind = "document"
            semantic, combined = self.analyze_document(
                file_bytes=file_bytes,
                original_filename=original_filename,
                mime_type=mime_type,
                user_description=user_description,
            )
        return kind, semantic, combined


class FakeLearningAwareGroqAgent:
    model = "test-memory-model"

    def __init__(self):
        class _Completions:
            def create(inner_self, *, model, messages, temperature=0.1, max_completion_tokens=700):
                system = str(messages[0].get("content", ""))
                user = str(messages[-1].get("content", ""))

                if "update-understanding layer" in system:
                    content = (
                        '{"relation":"NO_PRIOR_CONTEXT","related_memory_ids":[],'
                        '"understanding":"No earlier matching record.",'
                        '"reply":"I treated this as a new project update.",'
                        '"missing_information":"No earlier matching record."}'
                    )
                elif "grounded project-memory assistant" in system:
                    content = "The stored project memory provides the requested project-specific context."
                elif "friendly, concise assistant" in system:
                    content = "Here is the general answer using the available project context."
                else:
                    content = "Test Groq response."

                return _FakeGroqResponse(content)

        class _Chat:
            def __init__(self):
                self.completions = _Completions()
                self.chat = self

        self.client = _Chat()


class FakeNormalChatClient:
    def __init__(self):
        self.client = types.SimpleNamespace(
            chat=types.SimpleNamespace(
                completions=types.SimpleNamespace(
                    create=self.create
                )
            )
        )

    def create(self, *args, **kwargs):
        return _FakeGroqResponse("Normal Groq response with current-chat context.")


@pytest.fixture
def test_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    storage_path = os.path.join(temp_dir, "storage")
    data_dir = os.path.join(temp_dir, "memory-data")
    os.makedirs(storage_path, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    test_db = AppDatabase(db_path=db_path)
    project_repo = ProjectRepository(database=test_db)
    chat_repo = ChatRepository(database=test_db)
    message_repo = MessageRepository(database=test_db)
    evidence_repo = EvidenceRepository(database=test_db)
    file_storage = FileStorageService(root_dir=storage_path)

    fake_memory = FakeMemoryService()
    fake_evidence = FakeEvidenceUnderstandingService()
    fake_normal_groq = FakeGroqClient = FakeNormalChatClient()

    project_service = ProjectService(
        project_repo=project_repo,
        memory_service=fake_memory,
        canonical_db_path=os.path.join(data_dir, "memory_registry.db"),
        learning_data_dir=data_dir,
    )
    chat_service = ChatService(
        chat_repo=chat_repo,
        project_repo=project_repo,
    )
    normal_chat = NormalChatService(
        groq_client=fake_normal_groq,
        model="test-general-model",
    )

    def runtime_factory(**kwargs):
        project_id = kwargs["project_id"]
        return ProjectMemoryRuntime(
            **kwargs,
            message_repo=message_repo,
            evidence_repo=evidence_repo,
            db_dir=data_dir,
            memory_service=fake_memory,
            canonical_memory_service=CanonicalMemoryService(
                db_path=os.path.join(data_dir, "memory_registry.db")
            ),
            learning_repository=SQLiteLearningRepository(
                db_path=os.path.join(data_dir, f"learning_{project_id}.db")
            ),
            groq_agent=FakeLearningAwareGroqAgent(),
        )

    chat_runtime = ChatRuntimeService(
        project_repo=project_repo,
        chat_repo=chat_repo,
        message_repo=message_repo,
        evidence_repo=evidence_repo,
        normal_chat=normal_chat,
        memory_runtime_factory=runtime_factory,
    )

    return {
        "db": test_db,
        "temp_dir": temp_dir,
        "data_dir": data_dir,
        "project_repo": project_repo,
        "chat_repo": chat_repo,
        "message_repo": message_repo,
        "evidence_repo": evidence_repo,
        "file_storage": file_storage,
        "project_service": project_service,
        "chat_service": chat_service,
        "chat_runtime": chat_runtime,
        "fake_memory": fake_memory,
        "fake_evidence": fake_evidence,
    }


@pytest.fixture
def client(test_env, monkeypatch):
    from app.api import deps

    monkeypatch.setattr(deps, "_project_repo", test_env["project_repo"])
    monkeypatch.setattr(deps, "_chat_repo", test_env["chat_repo"])
    monkeypatch.setattr(deps, "_message_repo", test_env["message_repo"])
    monkeypatch.setattr(deps, "_evidence_repo", test_env["evidence_repo"])
    monkeypatch.setattr(deps, "_file_storage", test_env["file_storage"])
    monkeypatch.setattr(deps, "_evidence_understanding", test_env["fake_evidence"])
    monkeypatch.setattr(deps, "_project_service", test_env["project_service"])
    monkeypatch.setattr(deps, "_chat_service", test_env["chat_service"])
    monkeypatch.setattr(deps, "_chat_runtime_service", test_env["chat_runtime"])

    with TestClient(app) as c:
        yield c

    shutil.rmtree(test_env["temp_dir"], ignore_errors=True)
