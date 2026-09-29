import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from app.api.deps import (
    get_chat_repo,
    get_evidence_repo,
    get_evidence_understanding,
    get_file_storage,
    get_project_repo,
    get_chat_runtime_service,
)
from app.repositories.chat_repository import ChatRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import EvidenceResponse
from app.services.evidence_understanding_service import GroqEvidenceUnderstandingService
from app.services.file_storage_service import FileStorageService
from app.services.chat_runtime_service import ChatRuntimeService

router = APIRouter()


@router.post(
    "/chats/{chat_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    chat_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    chat_repo: ChatRepository = Depends(get_chat_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    evidence_repo: EvidenceRepository = Depends(get_evidence_repo),
    file_storage: FileStorageService = Depends(get_file_storage),
    evidence_understanding: GroqEvidenceUnderstandingService = Depends(
        get_evidence_understanding
    ),
    chat_runtime: ChatRuntimeService = Depends(get_chat_runtime_service),
):
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

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty."},
        )

    orig_filename = file.filename or "uploaded_file"
    mime_type = file.content_type or "application/octet-stream"
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

    try:
        kind, semantic_desc, combined_understanding = (
            evidence_understanding.process_evidence(
                file_bytes=file_bytes,
                original_filename=orig_filename,
                mime_type=mime_type,
                user_description=description,
            )
        )
    except Exception as e:
        kind = "file"
        semantic_desc = f"Analysis error: {str(e)}"
        combined_understanding = description or semantic_desc

    record = evidence_repo.create(
        evidence_id=evidence_id,
        project_id=project["project_id"],
        chat_id=chat_id,
        kind=kind,
        original_filename=orig_filename,
        mime_type=mime_type,
        storage_key=storage_key,
        sha256=sha256,
        size_bytes=size_bytes,
        user_description=description,
        semantic_description=semantic_desc,
        combined_understanding=combined_understanding,
    )

    # A standalone evidence upload is also project knowledge when Memory is ON.
    # Memory OFF still stores/analyzes the file for the current workspace, but
    # does not retain semantic content in Hindsight.
    try:
        chat_runtime.retain_evidence_for_chat(
            chat_id=chat_id,
            evidence_items=[record],
        )
        refreshed = evidence_repo.get(evidence_id)
        if refreshed:
            record = refreshed
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EVIDENCE_MEMORY_PROCESSING_FAILED",
                "message": str(e),
            },
        )

    return record


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
def get_evidence_metadata(
    evidence_id: str,
    evidence_repo: EvidenceRepository = Depends(get_evidence_repo),
):
    record = evidence_repo.get(evidence_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVIDENCE_NOT_FOUND", "message": f"Evidence {evidence_id} not found."},
        )
    return record


@router.get("/evidence/{evidence_id}/content")
def get_evidence_content(
    evidence_id: str,
    evidence_repo: EvidenceRepository = Depends(get_evidence_repo),
    file_storage: FileStorageService = Depends(get_file_storage),
):
    record = evidence_repo.get(evidence_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVIDENCE_NOT_FOUND", "message": f"Evidence {evidence_id} not found."},
        )

    try:
        file_bytes = file_storage.read_bytes(
            record["storage_key"],
            project_id=record["project_id"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_ACCESS_ERROR", "message": str(e)},
        )

    return Response(
        content=file_bytes,
        media_type=record["mime_type"],
        headers={
            "Content-Disposition": f'inline; filename="{record["original_filename"]}"'
        },
    )
