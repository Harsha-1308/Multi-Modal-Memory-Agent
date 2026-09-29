import uuid
from typing import Any, Dict, List, Optional
from app.repositories.chat_repository import ChatRepository
from app.repositories.project_repository import ProjectRepository


class ChatService:
    def __init__(
        self,
        chat_repo: Optional[ChatRepository] = None,
        project_repo: Optional[ProjectRepository] = None,
    ):
        self.chat_repo = chat_repo or ChatRepository()
        self.project_repo = project_repo or ProjectRepository()

    def create_chat(
        self,
        *,
        project_id: str,
        name: str,
    ) -> Dict[str, Any]:
        project = self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        chat_id = f"chat-{uuid.uuid4().hex[:10]}"
        cleaned_name = name.strip() or "New Chat"

        chat = self.chat_repo.create(
            chat_id=chat_id,
            project_id=project_id,
            name=cleaned_name,
            memory_enabled=True,
        )
        return chat

    def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        return self.chat_repo.get(chat_id)

    def list_chats(self, project_id: str) -> List[Dict[str, Any]]:
        return self.chat_repo.list_for_project(project_id)

    def update_settings(
        self,
        chat_id: str,
        *,
        memory_enabled: bool,
    ) -> Dict[str, Any]:
        chat = self.chat_repo.get(chat_id)
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")

        updated = self.chat_repo.update_settings(
            chat_id,
            memory_enabled=memory_enabled,
        )
        if not updated:
            raise ValueError(f"Failed to update chat {chat_id}")
        return updated
