import uuid
from typing import Optional

from app.services.canonical_memory_service import (
    CanonicalMemoryService,
)
from app.storage.repository_factory import (
    create_learning_repository,
)


class ExperienceService:
    """
    Creates persistent experiences linked to canonical memories.

    Experience is an event:
        "The agent used memory X for task Y."

    It is intentionally separate from the memory itself.
    """

    def __init__(
        self,
        repository=None,
        canonical_memory_service=None,
    ):
        self.repository = (
            repository
            if repository is not None
            else create_learning_repository()
        )

        self.canonical_memory_service = (
            canonical_memory_service
            if canonical_memory_service is not None
            else CanonicalMemoryService()
        )

    def create(
        self,
        bank_id: str,
        canonical_memory_id: int,
        task: str,
        action: str,
        context: Optional[str] = None,
    ) -> dict:

        if not task or not task.strip():
            raise ValueError("task is required.")

        if not action or not action.strip():
            raise ValueError("action is required.")

        memory = self._get_canonical_memory(
            bank_id=bank_id,
            memory_id=canonical_memory_id,
        )

        if memory is None:
            raise ValueError(
                "Cannot create experience: canonical memory does not exist."
            )

        experience_id = str(uuid.uuid4())

        return self.repository.create_experience(
            experience_id=experience_id,
            bank_id=bank_id,
            canonical_memory_id=canonical_memory_id,
            task=task.strip(),
            action=action.strip(),
            context=context.strip()
            if isinstance(context, str)
            else context,
        )

    def get(self, experience_id: str):
        return self.repository.get_experience(
            experience_id=experience_id
        )

    def list_for_memory(
        self,
        bank_id: str,
        canonical_memory_id: int,
    ):
        return self.repository.list_experiences_for_memory(
            bank_id=bank_id,
            canonical_memory_id=canonical_memory_id,
        )

    def _get_canonical_memory(
        self,
        bank_id: str,
        memory_id: int,
    ):
        memories = (
            self.canonical_memory_service.list_memories(
                bank_id=bank_id
            )
        )

        for memory in memories:
            if memory["id"] == memory_id:
                return memory

        return None

    def close(self):
        self.repository.close()
        self.canonical_memory_service.close()