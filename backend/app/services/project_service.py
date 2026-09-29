import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.repositories.project_repository import ProjectRepository
from app.services.canonical_memory_service import CanonicalMemoryService
from app.services.memory_learning_state_service import MemoryLearningStateService
from app.services.memory_service import MemoryService
from app.repositories.sqlite.learning_repository import SQLiteLearningRepository

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(
        self,
        project_repo: Optional[ProjectRepository] = None,
        memory_service: Optional[MemoryService] = None,
        canonical_db_path: Optional[str] = None,
        learning_data_dir: Optional[str] = None,
    ):
        self.project_repo = project_repo or ProjectRepository()
        self.memory_service = memory_service or MemoryService()
        default_data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.canonical_db_path = Path(
            canonical_db_path or (default_data_dir / "memory_registry.db")
        )
        self.learning_data_dir = Path(
            learning_data_dir or default_data_dir
        )

    def create_project(
        self,
        *,
        name: str,
        project_type: str,
        description: str = "",
        seed_memories: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Project name cannot be empty")

        cleaned_type = project_type.strip()
        if not cleaned_type:
            cleaned_type = "code"

        project_id = f"proj-{uuid.uuid4().hex[:10]}"
        hindsight_bank_id = f"bank-{project_id}"

        # 1. Create Hindsight bank using existing MemoryService
        try:
            self.memory_service.create_project_bank(
                bank_id=hindsight_bank_id,
                project_name=cleaned_name,
                project_description=description.strip(),
            )
        except Exception as exc:
            logger.error(f"Failed to create Hindsight bank for project {project_id}: {exc}")
            raise RuntimeError(f"Hindsight bank creation failed: {str(exc)}")

        # 2. Retain optional seed memories if provided
        seeds = seed_memories or []
        if seeds:
            self.canonical_db_path.parent.mkdir(parents=True, exist_ok=True)
            self.learning_data_dir.mkdir(parents=True, exist_ok=True)
            canonical_service = CanonicalMemoryService(
                db_path=str(self.canonical_db_path)
            )
            self.learning_data_dir.mkdir(parents=True, exist_ok=True)
            learning_repo = SQLiteLearningRepository(
                db_path=str(self.learning_data_dir / f"learning_{project_id}.db")
            )
            learning_state_service = MemoryLearningStateService(repository=learning_repo)

            try:
                for seed in seeds:
                    text = (seed.get("text") or "").strip()
                    if not text:
                        continue
                    try:
                        registered = canonical_service.register(
                            hindsight_bank_id,
                            text,
                        )
                        if registered:
                            self.memory_service.retain(
                                bank_id=hindsight_bank_id,
                                content=text,
                            )
                        mem = canonical_service.get_memory(
                            hindsight_bank_id,
                            text,
                        )
                        if mem and mem.get("id"):
                            learning_state_service.refresh(mem["id"])
                    except Exception as exc:
                        logger.warning(f"Error seeding memory '{text}': {exc}")
            finally:
                canonical_service.close()
                learning_state_service.close()

        # 3. Create project record in SQLite
        project = self.project_repo.create(
            project_id=project_id,
            name=cleaned_name,
            project_type=cleaned_type,
            description=description.strip(),
            hindsight_bank_id=hindsight_bank_id,
        )

        return project

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self.project_repo.get(project_id)

    def list_projects(self) -> List[Dict[str, Any]]:
        return self.project_repo.list_all()

    def get_project_memories(self, project_id: str) -> List[Dict[str, Any]]:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        bank_id = project["hindsight_bank_id"]
        self.learning_data_dir.mkdir(parents=True, exist_ok=True)
        canonical_service = CanonicalMemoryService(
            db_path=str(self.canonical_db_path)
        )
        learning_repo = SQLiteLearningRepository(
            db_path=str(self.learning_data_dir / f"learning_{project_id}.db")
        )
        learning_state_service = MemoryLearningStateService(repository=learning_repo)
        from app.repositories.message_repository import MessageRepository
        message_repo = MessageRepository()

        try:
            memories = canonical_service.list_memories(bank_id)
            results = []
            for mem in memories:
                mid = mem["id"]
                state = learning_state_service.get_state(mid)
                sources = message_repo.find_memory_source(
                    project_id=project_id,
                    canonical_memory_id=mid,
                )
                results.append({
                    "canonical_memory_id": mid,
                    "text": mem["original_text"],
                    "created_at": mem["created_at"],
                    "learning_state": state,
                    "user_sources": [
                        {
                            "message_id": s["message_id"],
                            "chat_id": s["chat_id"],
                            "content": s["content"],
                            "created_at": s["created_at"],
                        }
                        for s in sources
                    ],
                })
            return results
        finally:
            canonical_service.close()
            learning_state_service.close()
