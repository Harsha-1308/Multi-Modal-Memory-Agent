from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import (
    get_chat_repo,
    get_chat_service,
    get_message_repo,
    get_project_repo,
)
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import ChatCreate, ChatResponse, ChatSettingsUpdate
from app.services.chat_service import ChatService

router = APIRouter()


@router.post(
    "/projects/{project_id}/chats",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat(
    project_id: str,
    data: ChatCreate,
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        return chat_service.create_chat(
            project_id=project_id,
            name=data.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CHAT_CREATION_FAILED", "message": str(e)},
        )


@router.get(
    "/projects/{project_id}/chats",
    response_model=List[ChatResponse],
)
def list_chats(
    project_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    project = project_repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found."},
        )
    return chat_service.list_chats(project_id)


@router.get("/chats/{chat_id}", response_model=ChatResponse)
def get_chat(
    chat_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_NOT_FOUND", "message": f"Chat {chat_id} not found."},
        )
    return chat


@router.patch("/chats/{chat_id}/settings", response_model=ChatResponse)
def update_chat_settings(
    chat_id: str,
    data: ChatSettingsUpdate,
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        return chat_service.update_settings(
            chat_id=chat_id,
            memory_enabled=data.memory_enabled,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_NOT_FOUND", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SETTINGS_UPDATE_FAILED", "message": str(e)},
        )


@router.get("/chats/{chat_id}/messages")
def get_chat_messages(
    chat_id: str,
    chat_repo: ChatRepository = Depends(get_chat_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
):
    chat = chat_repo.get(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_NOT_FOUND", "message": f"Chat {chat_id} not found."},
        )
    return message_repo.list_for_chat(chat_id)
