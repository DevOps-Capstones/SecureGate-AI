from collections import Counter
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.database import get_db
from app.models.scan import Scan
from app.schemas.scans import (
    DashboardSummaryResponse,
    ScanCreate,
    ScanCreateResponse,
    ScanDetailsResponse,
    ScanSummary,
    ToolReportResponse,
    ToolReportUploadResponse,
)
from app.services.scan_orchestrator import create_scan_record, get_dashboard_summary, ingest_tool_report

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


def _scan_details_response(scan: Scan) -> ScanDetailsResponse:
    counts = Counter(finding.severity for finding in scan.findings)
    return ScanDetailsResponse(
        scan_id=scan.scan_id,
        project_name=scan.project_name,
        repository_url=scan.repository_url,
        branch=scan.branch,
        commit_sha=scan.commit_sha,
        status=scan.status,
        received_at=scan.received_at,
        completed_at=scan.completed_at,
        uploaded_reports=scan.tool_reports,
        finding_counts=dict(counts),
        tool_status={report.tool_name: report.status for report in scan.tool_reports},
        findings=scan.findings,
    )


@router.post(
    "",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit scan metadata",
    description="Creates a scan record for reports produced by GitHub Actions. SecureGate AI does not execute scanners.",
    responses={201: {"description": "Scan metadata received"}},
)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)) -> ScanCreateResponse:
    scan = create_scan_record(
        db=db,
        project_name=payload.project_name,
        repository_url=payload.repository_url,
        branch=payload.branch,
        commit_sha=payload.commit_sha,
    )
    return ScanCreateResponse(scan_id=scan.scan_id, status=scan.status)


@router.get(
    "",
    response_model=list[ScanSummary],
    summary="List recent scans",
    description="Returns recent scan records received from CI pipelines.",
)
def list_scans(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)) -> list[Scan]:
    return list(db.execute(select(Scan).order_by(Scan.received_at.desc()).limit(limit)).scalars().all())


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    summary="Get dashboard summary",
    description="Returns project totals, scan totals, recent scans, latest uploads, and recent findings.",
)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(**get_dashboard_summary(db))


def _upload_report(scan_id: str, tool_name: str, payload: dict[str, Any] | list[Any], db: Session) -> ToolReportUploadResponse:
    try:
        scan, report, findings = ingest_tool_report(db, scan_id, tool_name, payload)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found") from None
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ToolReportUploadResponse(
        scan_id=scan.scan_id,
        tool=report.tool_name,
        status=report.status,
        findings_count=len(findings),
        uploaded_at=report.uploaded_at,
    )


@router.post("/{scan_id}/gitleaks", response_model=ToolReportUploadResponse, summary="Upload GitLeaks JSON report")
def upload_gitleaks_report(
    scan_id: str,
    payload: dict[str, Any] | list[Any] = Body(..., examples=[[{"RuleID": "generic-api-key", "File": ".env"}]]),
    db: Session = Depends(get_db),
) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "gitleaks", payload, db)


@router.post("/{scan_id}/trivy-fs", response_model=ToolReportUploadResponse, summary="Upload Trivy filesystem JSON report")
def upload_trivy_fs_report(
    scan_id: str,
    payload: dict[str, Any] = Body(..., examples=[{"Results": []}]),
    db: Session = Depends(get_db),
) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "trivy-fs", payload, db)


@router.post("/{scan_id}/trivy-image", response_model=ToolReportUploadResponse, summary="Upload Trivy image JSON report")
def upload_trivy_image_report(
    scan_id: str,
    payload: dict[str, Any] = Body(..., examples=[{"Results": []}]),
    db: Session = Depends(get_db),
) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "trivy-image", payload, db)


@router.post("/{scan_id}/sonarqube", response_model=ToolReportUploadResponse, summary="Upload SonarQube JSON report")
def upload_sonarqube_report(
    scan_id: str,
    payload: dict[str, Any] = Body(..., examples=[{"projectStatus": {"status": "OK"}, "issues": []}]),
    db: Session = Depends(get_db),
) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "sonarqube", payload, db)


@router.get(
    "/{scan_id}",
    response_model=ScanDetailsResponse,
    summary="Get scan details",
    description="Returns scan metadata, uploaded report status, normalized findings, and finding counts.",
)
def get_scan(scan_id: str, db: Session = Depends(get_db)) -> ScanDetailsResponse:
    scan = db.execute(
        select(Scan)
        .where(Scan.scan_id == scan_id)
        .options(selectinload(Scan.tool_reports), selectinload(Scan.findings))
    ).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return _scan_details_response(scan)
