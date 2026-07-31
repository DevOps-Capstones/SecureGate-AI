from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.scans import PipelineCompleteRequest, PipelineStartRequest, ScanCreateResponse
from app.services.auth import require_pipeline_api_key
from app.services.scan_orchestrator import complete_pipeline, create_scan_record

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"], dependencies=[Depends(require_pipeline_api_key)])


@router.post("/start", response_model=ScanCreateResponse, status_code=status.HTTP_201_CREATED, summary="Start CI pipeline scan lifecycle")
def pipeline_start(payload: PipelineStartRequest, db: Session = Depends(get_db)) -> ScanCreateResponse:
    try:
        scan = create_scan_record(
            db=db,
            project_name=payload.project_name,
            repository_url=payload.repository_url,
            branch=payload.branch,
            commit_sha=payload.commit_sha,
            pipeline_run_id=payload.pipeline_run_id,
            actor="github-actions",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return ScanCreateResponse(scan_id=scan.scan_id, status=scan.status)


@router.post("/complete", response_model=ScanCreateResponse, summary="Complete CI pipeline scan lifecycle")
def pipeline_complete(payload: PipelineCompleteRequest, db: Session = Depends(get_db)) -> ScanCreateResponse:
    try:
        scan = complete_pipeline(db, payload.scan_id, payload.status)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found") from None
    return ScanCreateResponse(scan_id=scan.scan_id, status=scan.status)
