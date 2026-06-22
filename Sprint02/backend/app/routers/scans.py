from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.database import get_db
from app.models.scan import Scan
from app.schemas.scans import ScanCreate, ScanCreateResponse, ScanDetailsResponse, ScanSummary
from app.services.scan_orchestrator import run_repository_scan

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


@router.post(
    "",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run a repository security scan",
    description="Clones a repository, runs GitLeaks and Trivy filesystem scans, evaluates the security gate, stores results, and returns the deployment decision.",
)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)) -> ScanCreateResponse:
    scan = run_repository_scan(db, payload.repository_url)
    return ScanCreateResponse(
        scan_id=scan.scan_id,
        status=scan.status,
        deployment_approved=scan.deployment_approved,
        critical_count=scan.critical_count,
        high_count=scan.high_count,
        medium_count=scan.medium_count,
        secrets_count=scan.secrets_count,
    )


@router.get(
    "",
    response_model=list[ScanSummary],
    summary="List recent scans",
    description="Returns recent repository scan summaries for dashboard widgets.",
)
def list_scans(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)) -> list[Scan]:
    return list(
        db.execute(select(Scan).order_by(Scan.started_at.desc()).limit(limit)).scalars().all()
    )


@router.get(
    "/{scan_id}",
    response_model=ScanDetailsResponse,
    summary="Get scan details",
    description="Returns scan metadata, GitLeaks findings, Trivy findings, and deployment status.",
)
def get_scan(scan_id: str, db: Session = Depends(get_db)) -> ScanDetailsResponse:
    scan = db.execute(
        select(Scan)
        .where(Scan.scan_id == scan_id)
        .options(selectinload(Scan.findings))
    ).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    gitleaks_findings = [finding for finding in scan.findings if finding.scanner_type == "gitleaks"]
    trivy_findings = [finding for finding in scan.findings if finding.scanner_type == "trivy"]

    return ScanDetailsResponse(
        scan_id=scan.scan_id,
        repository_url=scan.repository_url,
        status=scan.status,
        deployment_approved=scan.deployment_approved,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        critical_count=scan.critical_count,
        high_count=scan.high_count,
        medium_count=scan.medium_count,
        low_count=scan.low_count,
        secrets_count=scan.secrets_count,
        gitleaks_findings=gitleaks_findings,
        trivy_findings=trivy_findings,
    )
