import json
import uuid
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.api.deps import (
    get_chat_repo,
    get_chat_runtime_service,
    get_evidence_repo,
    get_evidence_understanding,
    get_file_storage,
    get_project_repo,
)
from app.repositories.chat_repository import ChatRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import MessageResponse
from app.services.chat_runtime_service import ChatRuntimeService
from app.services.evidence_understanding_service import GroqEvidenceUnderstandingService
from app.services.file_storage_service import FileStorageService

router = APIRouter()


@router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def send_message(
    chat_id: str,
    content: str = Form(""),
    files: Optional[List[UploadFile]] = File(None),
    attachment_descriptions: Optional[str] = Form(None),
    chat_repo: ChatRepository = Depends(get_chat_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    evidence_repo: EvidenceRepository = Depends(get_evidence_repo),
    file_storage: FileStorageService = Depends(get_file_storage),
    evidence_understanding: GroqEvidenceUnderstandingService = Depends(
        get_evidence_understanding
    ),
    chat_runtime: ChatRuntimeService = Depends(get_chat_runtime_service),
):
    # 0. Reject only a truly empty request. Evidence-only messages are valid.
    if not (content or "").strip() and not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_MESSAGE",
                "message": "Send a message or attach at least one evidence file.",
            },
        )

    # 1. Load chat & project
    chat = chat_repo.get(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAT_NOT_FOUND", "message": f"Chat {chat_id} not found."},
        )

    project = project_repo.get(chat["project_id"])
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": "Associated project not found."},
        )

    # 2. Parse attachment descriptions
    descriptions_map = {}
    if attachment_descriptions:
        try:
            parsed = json.loads(attachment_descriptions)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "index" in item and "description" in item:
                        descriptions_map[int(item["index"])] = str(item["description"])
            elif isinstance(parsed, dict):
                descriptions_map = {int(k): str(v) for k, v in parsed.items() if str(k).isdigit()}
        except Exception:
            descriptions_map = {}

    # 3. Process uploaded files
    evidence_objects = []
    if files:
        for idx, file_upload in enumerate(files):
            file_bytes = await file_upload.read()
            if not file_bytes:
                continue

            orig_filename = file_upload.filename or f"upload_{idx}"
            mime_type = file_upload.content_type or "application/octet-stream"
            user_desc = descriptions_map.get(idx)

            evidence_id = f"ev-{uuid.uuid4().hex[:10]}"

            try:
                storage_key, sha256, size_bytes = file_storage.store_evidence_file(
                    project_id=project["project_id"],
                    evidence_id=evidence_id,
                    file_bytes=file_bytes,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "STORAGE_ERROR", "message": str(e)},
                )

            # Analyze evidence (vision/document understanding)
            try:
                kind, semantic_desc, combined_understanding = (
                    evidence_understanding.process_evidence(
                        file_bytes=file_bytes,
                        original_filename=orig_filename,
                        mime_type=mime_type,
                        user_description=user_desc,
                    )
                )
            except Exception as e:
                kind = "file"
                semantic_desc = f"Analysis error: {str(e)}"
                combined_understanding = user_desc or semantic_desc

            # Store in evidence repository
            ev_record = evidence_repo.create(
                evidence_id=evidence_id,
                project_id=project["project_id"],
                chat_id=chat_id,
                kind=kind,
                original_filename=orig_filename,
                mime_type=mime_type,
                storage_key=storage_key,
                sha256=sha256,
                size_bytes=size_bytes,
                user_description=user_desc,
                semantic_description=semantic_desc,
                combined_understanding=combined_understanding,
            )
            evidence_objects.append(ev_record)

    # 4. Route to ChatRuntimeService
    try:
        response = await asyncio.to_thread(
    chat_runtime.handle_message,
    chat_id=chat_id,
    content=content,
    evidence_items=evidence_objects,
)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "MESSAGE_PROCESSING_FAILED", "message": str(e)},
        )
