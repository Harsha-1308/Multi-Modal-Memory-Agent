from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import (
    get_message_repo,
    get_project_repo,
    get_project_service,
)
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import ProjectCreate, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter()


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    data: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        seeds = (
            [{"text": s.text} for s in data.seed_memories]
            if data.seed_memories
            else None
        )
        project = project_service.create_project(
            name=data.name,
            project_type=data.project_type,
            description=data.description,
            seed_memories=seeds,
        )
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PROJECT_CREATION_FAILED", "message": str(e)},
        )


@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    project_service: ProjectService = Depends(get_project_service),
):
    return project_service.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found."},
        )
    return project


@router.get("/projects/{project_id}/memories")
def get_project_memories(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
):
    try:
        return project_service.get_project_memories(project_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "MEMORY_QUERY_FAILED", "message": str(e)},
        )


@router.get("/projects/{project_id}/history")
def get_project_history(
    project_id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
):
    project = project_repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found."},
        )
    return message_repo.list_for_project(project_id)
