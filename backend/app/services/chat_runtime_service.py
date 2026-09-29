from typing import Any, Callable, Dict, List, Optional
from app.repositories.chat_repository import ChatRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.services.normal_chat_service import NormalChatService
from app.services.project_memory_runtime import ProjectMemoryRuntime


class ChatRuntimeService:
    def __init__(
        self,
        project_repo: Optional[ProjectRepository] = None,
        chat_repo: Optional[ChatRepository] = None,
        message_repo: Optional[MessageRepository] = None,
        evidence_repo: Optional[EvidenceRepository] = None,
        normal_chat: Optional[NormalChatService] = None,
        memory_runtime_factory: Optional[Callable[..., ProjectMemoryRuntime]] = None,
    ):
        self.project_repo = project_repo or ProjectRepository()
        self.chat_repo = chat_repo or ChatRepository()
        self.message_repo = message_repo or MessageRepository()
        self.evidence_repo = evidence_repo or EvidenceRepository()
        self.normal_chat = normal_chat or NormalChatService()
        self.memory_runtime_factory = memory_runtime_factory

    def _build_memory_runtime(self, *, chat: Dict[str, Any], project: Dict[str, Any]) -> ProjectMemoryRuntime:
        factory = self.memory_runtime_factory
        if factory is None:
            return ProjectMemoryRuntime(
                project_id=project["project_id"],
                bank_id=project["hindsight_bank_id"],
                chat_id=chat["chat_id"],
                project_name=project["name"],
                project_description=project["description"],
                message_repo=self.message_repo,
                evidence_repo=self.evidence_repo,
            )
        return factory(
            project_id=project["project_id"],
            bank_id=project["hindsight_bank_id"],
            chat_id=chat["chat_id"],
            project_name=project["name"],
            project_description=project["description"],
        )

    def retain_evidence_for_chat(
        self,
        *,
        chat_id: str,
        evidence_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Retain standalone evidence only when the chat's Memory mode is ON."""
        chat = self.chat_repo.get(chat_id)
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")
        project = self.project_repo.get(chat["project_id"])
        if not project:
            raise ValueError(f"Project {chat['project_id']} not found")

        if not chat.get("memory_enabled", True):
            return evidence_items

        runtime = self._build_memory_runtime(chat=chat, project=project)
        runtime.retain_evidence(evidence_items)
        return evidence_items

    def handle_message(
        self,
        *,
        chat_id: str,
        content: str,
        evidence_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        chat = self.chat_repo.get(chat_id)
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")

        project = self.project_repo.get(chat["project_id"])
        if not project:
            raise ValueError(f"Project {chat['project_id']} not found")

        evidence_objects = evidence_items or []
        evidence_descriptions = [
            e.get("combined_understanding") or e.get("user_description") or e.get("original_filename")
            for e in evidence_objects
            if e.get("combined_understanding") or e.get("user_description") or e.get("original_filename")
        ]

        # ----------------------------------------------------
        # MEMORY ON PATH
        # ----------------------------------------------------
        if chat.get("memory_enabled", True):
            runtime = self._build_memory_runtime(chat=chat, project=project)

            result = runtime.handle_message(
                content=content,
                evidence_descriptions=evidence_descriptions,
                evidence_objects=evidence_objects,
            )

            user_message_id = result.get("user_message_id")
            if user_message_id:
                for evidence in evidence_objects:
                    evidence_id = evidence.get("evidence_id")
                    if evidence_id:
                        self.evidence_repo.attach_to_message(
                            evidence_id=evidence_id,
                            message_id=user_message_id,
                        )
            return result

        # ----------------------------------------------------
        # MEMORY OFF PATH
        # ----------------------------------------------------
        # 1. Save user message
        user_msg = self.message_repo.create(
            chat_id=chat_id,
            role="user",
            content=content or (evidence_descriptions[0] if evidence_descriptions else ""),
            message_type="GENERAL_QUERY",
            metadata={"memory_enabled": False, "attachments_count": len(evidence_objects)},
        )

        # 2. Get chat history for this chat ONLY
        history = [
            item
            for item in self.message_repo.list_for_chat(chat_id)
            if item.get("message_id") != user_msg.get("message_id")
        ]

        # 3. Call NormalChatService
        answer = self.normal_chat.answer(
            user_message=content,
            chat_history=history,
            evidence_descriptions=evidence_descriptions,
            project_name=project["name"],
        )

        # 4. Save assistant response
        evidence_sources = [
            {
                "rank": index,
                "source_type": "uploaded_evidence",
                "source_kind": evidence.get("kind") or "file",
                "evidence_id": evidence.get("evidence_id"),
                "canonical_memory_id": None,
                "original_filename": evidence.get("original_filename"),
                "mime_type": evidence.get("mime_type"),
                "user_description": evidence.get("user_description"),
                "semantic_description": evidence.get("semantic_description"),
                "combined_understanding": evidence.get("combined_understanding"),
                "storage_key": evidence.get("storage_key"),
                "sha256": evidence.get("sha256"),
                "size_bytes": evidence.get("size_bytes"),
                "hindsight_memory": None,
            }
            for index, evidence in enumerate(evidence_objects, start=1)
        ]

        assistant_msg = self.message_repo.create(
            chat_id=chat_id,
            role="assistant",
            content=answer,
            message_type="GENERAL_QUERY_REPLY",
            metadata={
                "memory_enabled": False,
                "evidence": {
                    "source_evidence": evidence_sources,
                    "learning_evidence": {},
                    "understanding": {
                        "note": "Memory disabled. Evidence was analyzed for this response only."
                    },
                    "metrics": {},
                },
            },
        )

        for evidence in evidence_objects:
            evidence_id = evidence.get("evidence_id")
            if evidence_id:
                updated = self.evidence_repo.attach_to_message(
                    evidence_id=evidence_id,
                    message_id=user_msg["message_id"],
                )
                if updated:
                    evidence.update(updated)

        # 5. Return standardized Memory OFF response
        return {
            "message": {
                "message_id": assistant_msg["message_id"],
                "role": "assistant",
                "content": answer,
                "created_at": assistant_msg["created_at"],
            },
            "memory": {
                "enabled": False,
                "mode": "general",
                "status": "disabled",
            },
            "evidence": {
                "source_evidence": evidence_sources,
                "learning_evidence": {},
                "understanding": {
                    "note": "Memory disabled. Evidence was analyzed for this response only; no project-memory retention or learning was performed."
                },
                "metrics": {},
            },
            "attachments": evidence_objects,
            "user_message_id": user_msg["message_id"],
        }
