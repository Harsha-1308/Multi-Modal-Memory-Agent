from app.repositories.chat_repository import ChatRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.services.chat_runtime_service import ChatRuntimeService
from app.services.chat_service import ChatService
from app.services.evidence_understanding_service import GroqEvidenceUnderstandingService
from app.services.file_storage_service import FileStorageService
from app.services.project_service import ProjectService

_project_repo = ProjectRepository()
_chat_repo = ChatRepository()
_message_repo = MessageRepository()
_evidence_repo = EvidenceRepository()
_file_storage = FileStorageService()
_evidence_understanding = GroqEvidenceUnderstandingService()
_project_service = ProjectService(project_repo=_project_repo)
_chat_service = ChatService(chat_repo=_chat_repo, project_repo=_project_repo)
_chat_runtime_service = ChatRuntimeService(
    project_repo=_project_repo,
    chat_repo=_chat_repo,
    message_repo=_message_repo,
    evidence_repo=_evidence_repo,
)


def get_project_repo() -> ProjectRepository:
    return _project_repo


def get_chat_repo() -> ChatRepository:
    return _chat_repo


def get_message_repo() -> MessageRepository:
    return _message_repo


def get_evidence_repo() -> EvidenceRepository:
    return _evidence_repo


def get_file_storage() -> FileStorageService:
    return _file_storage


def get_evidence_understanding() -> GroqEvidenceUnderstandingService:
    return _evidence_understanding


def get_project_service() -> ProjectService:
    return _project_service


def get_chat_service() -> ChatService:
    return _chat_service


def get_chat_runtime_service() -> ChatRuntimeService:
    return _chat_runtime_service
