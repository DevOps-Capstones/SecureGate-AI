from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.scan import Project
from app.schemas.projects import ProjectCreate, ProjectFindingResponse, ProjectHealthResponse, ProjectResponse, ProjectTriggerScanRequest, ProjectTriggerScanResponse
from app.services.github_actions import trigger_github_actions_scan
from app.services.projects import build_project_findings, build_project_health, create_project, delete_project, load_project

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Register a project")
def register_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectResponse:
    try:
        project = create_project(db, payload.name, payload.repository_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse], summary="List registered projects")
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.execute(select(Project).order_by(Project.created_at.desc())).scalars().all())


@router.get("/{project_key}", response_model=ProjectHealthResponse, summary="Get project health")
def get_project(project_key: str, db: Session = Depends(get_db)) -> ProjectHealthResponse:
    project = load_project(db, project_key)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectHealthResponse(**build_project_health(project))


@router.get("/{project_key}/findings", response_model=list[ProjectFindingResponse], summary="List historical project findings")
def get_project_findings(project_key: str, finding_status: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db)) -> list[ProjectFindingResponse]:
    project = load_project(db, project_key)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [ProjectFindingResponse(**item) for item in build_project_findings(project, finding_status)]


@router.post("/{project_key}/trigger-scan", response_model=ProjectTriggerScanResponse, summary="Trigger a GitHub Actions scan for a project")
def trigger_project_scan(project_key: str, payload: ProjectTriggerScanRequest | None = None, db: Session = Depends(get_db)) -> ProjectTriggerScanResponse:
    project = load_project(db, project_key)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    request_payload = payload or ProjectTriggerScanRequest()
    if request_payload.runner != "github-actions":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only github-actions runner is supported right now")
    try:
        result = trigger_github_actions_scan(project, request_payload.branch or "main")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ProjectTriggerScanResponse(**result.__dict__)


@router.delete("/{project_key}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a project")
def remove_project(project_key: str, db: Session = Depends(get_db)) -> None:
    deleted = delete_project(db, project_key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db.commit()
