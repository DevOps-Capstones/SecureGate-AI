from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.database import get_db
from app.models.scan import AuditLog, Notification, Scan, ToolReport
from app.schemas.scans import (
    AuditLogResponse,
    DashboardSummaryResponse,
    ScanCreate,
    ScanCreateResponse,
    ScanDetailsResponse,
    ScanSummary,
    TimelineEventResponse,
    ToolReportResponse,
    ToolReportUploadResponse,
)
from app.services.auth import require_pipeline_api_key
from app.services.scan_orchestrator import create_scan_record, get_dashboard_summary, ingest_tool_report
from app.services.report_export import generate_tool_report_pdf

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


def _timeline(scan: Scan) -> list[TimelineEventResponse]:
    return [
        TimelineEventResponse(label="Scan Created", status="DONE" if scan.received_at else "PENDING", timestamp=scan.received_at),
        TimelineEventResponse(label="Reports Uploaded", status="DONE" if len(scan.tool_reports) > 0 else "PENDING", timestamp=max((report.uploaded_at for report in scan.tool_reports), default=None)),
        TimelineEventResponse(label="Scoring Completed", status="DONE" if scan.scoring_at else "PENDING", timestamp=scan.scoring_at),
        TimelineEventResponse(label="Report Generated", status="DONE" if scan.report_generation_at else "PENDING", timestamp=scan.report_generation_at),
        TimelineEventResponse(label="Notification Sent", status="DONE" if scan.notification_sent_at else "PENDING", timestamp=scan.notification_sent_at),
        TimelineEventResponse(label="Completed", status="DONE" if scan.completed_at else "FAILED" if scan.failed_at else "PENDING", timestamp=scan.completed_at or scan.failed_at),
    ]


def _scan_details_response(scan: Scan) -> ScanDetailsResponse:
    counts = Counter(finding.severity for finding in scan.findings)
    uploaded_reports = [
        ToolReportResponse.model_validate(report).model_copy(update={"scan_id": scan.scan_id})
        for report in scan.tool_reports
    ]
    return ScanDetailsResponse(
        scan_id=scan.scan_id,
        project_key=scan.project.project_key if scan.project else None,
        project_name=scan.project_name,
        repository_url=scan.repository_url,
        image_name=scan.image_name,
        image_tag=scan.image_tag,
        image_full_path=scan.image_full_path,
        branch=scan.branch,
        commit_sha=scan.commit_sha,
        status=scan.status,
        pipeline_run_id=scan.pipeline_run_id,
        pipeline_status=scan.pipeline_status,
        received_at=scan.received_at,
        processing_at=scan.processing_at,
        scoring_at=scan.scoring_at,
        report_generation_at=scan.report_generation_at,
        notification_sent_at=scan.notification_sent_at,
        completed_at=scan.completed_at,
        failed_at=scan.failed_at,
        security_score=scan.security_score,
        deployment_decision=scan.deployment_decision,
        sonar_quality_gate=scan.sonar_quality_gate,
        uploaded_reports=uploaded_reports,
        finding_counts=dict(counts),
        tool_status={report.tool_name: report.status for report in scan.tool_reports},
        findings=scan.findings,
        timeline=_timeline(scan),
        notifications=scan.notifications,
        audit_logs=scan.audit_logs,
    )


@router.post(
    "",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit scan metadata",
    description="Creates a scan record for reports produced by CI systems. SecureGate AI does not execute scanners.",
    responses={201: {"description": "Scan metadata received"}},
)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)) -> ScanCreateResponse:
    try:
        scan = create_scan_record(
            db=db,
            project_name=payload.project_name,
            repository_url=payload.repository_url,
            branch=payload.branch,
            commit_sha=payload.commit_sha,
            actor="manual",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ScanCreateResponse(scan_id=scan.scan_id, status=scan.status)


@router.get("", response_model=list[ScanSummary], summary="List recent scans")
def list_scans(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)) -> list[Scan]:
    return list(db.execute(select(Scan).order_by(Scan.received_at.desc()).limit(limit)).scalars().all())


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse, summary="Get dashboard summary")
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


@router.post("/{scan_id}/gitleaks", response_model=ToolReportUploadResponse, summary="Upload GitLeaks JSON report", dependencies=[Depends(require_pipeline_api_key)])
def upload_gitleaks_report(scan_id: str, payload: dict[str, Any] | list[Any] = Body(..., examples=[[{"RuleID": "generic-api-key", "File": ".env"}]]), db: Session = Depends(get_db)) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "gitleaks", payload, db)


@router.post("/{scan_id}/semgrep", response_model=ToolReportUploadResponse, summary="Upload Semgrep JSON report", dependencies=[Depends(require_pipeline_api_key)])
def upload_semgrep_report(scan_id: str, payload: dict[str, Any] = Body(..., examples=[{"results": []}]), db: Session = Depends(get_db)) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "semgrep", payload, db)


@router.post("/{scan_id}/trivy-fs", response_model=ToolReportUploadResponse, summary="Upload Trivy filesystem JSON report", dependencies=[Depends(require_pipeline_api_key)])
def upload_trivy_fs_report(scan_id: str, payload: dict[str, Any] = Body(..., examples=[{"Results": []}]), db: Session = Depends(get_db)) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "trivy-fs", payload, db)


@router.post("/{scan_id}/trivy-image", response_model=ToolReportUploadResponse, summary="Upload Trivy image JSON report", dependencies=[Depends(require_pipeline_api_key)])
def upload_trivy_image_report(scan_id: str, payload: dict[str, Any] = Body(..., examples=[{"Results": []}]), db: Session = Depends(get_db)) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "trivy-image", payload, db)


@router.post("/{scan_id}/sonarqube", response_model=ToolReportUploadResponse, summary="Upload SonarQube JSON report", dependencies=[Depends(require_pipeline_api_key)])
def upload_sonarqube_report(scan_id: str, payload: dict[str, Any] = Body(..., examples=[{"projectStatus": {"status": "OK"}, "issues": []}]), db: Session = Depends(get_db)) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "sonarqube", payload, db)


@router.post("/{scan_id}/unit-tests", response_model=ToolReportUploadResponse, summary="Upload unit-test JSON report", dependencies=[Depends(require_pipeline_api_key)])
def upload_unit_tests_report(scan_id: str, payload: dict[str, Any] = Body(..., examples=[{"status": "PASSED"}]), db: Session = Depends(get_db)) -> ToolReportUploadResponse:
    return _upload_report(scan_id, "unit-tests", payload, db)


@router.get("/{scan_id}/reports/{tool_name}", summary="Download uploaded raw tool report")
def download_tool_report(scan_id: str, tool_name: str, db: Session = Depends(get_db)) -> FileResponse:
    row = db.execute(
        select(ToolReport)
        .join(Scan, ToolReport.scan_pk == Scan.id)
        .where(Scan.scan_id == scan_id, ToolReport.tool_name == tool_name)
    ).scalar_one_or_none()
    if not row or not row.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool report not found")
    path = Path(row.file_path)
    if not path.exists():
        alt = Path.cwd() / row.file_path
        path = alt if alt.exists() else path
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored report file not found")
    filename = f"{scan_id}-{tool_name}-report.json"
    return FileResponse(path, media_type="application/json", filename=filename)


@router.get("/{scan_id}/reports/{tool_name}/pdf", summary="Download readable PDF for uploaded tool report")
def download_tool_report_pdf(scan_id: str, tool_name: str, db: Session = Depends(get_db)) -> FileResponse:
    scan = db.execute(
        select(Scan)
        .where(Scan.scan_id == scan_id)
        .options(selectinload(Scan.findings), selectinload(Scan.tool_reports))
    ).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    report = next((item for item in scan.tool_reports if item.tool_name == tool_name), None)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool report not found")
    findings = [item for item in scan.findings if item.tool_report_pk == report.id]
    base_path = Path(report.file_path or f"storage/scans/{scan.scan_id}/{tool_name}-report.json")
    if not base_path.is_absolute():
        base_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = base_path.with_suffix(".pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(generate_tool_report_pdf(scan, report, findings))
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{scan_id}-{tool_name}-report.pdf")


@router.get("/{scan_id}", response_model=ScanDetailsResponse, summary="Get scan details")
def get_scan(scan_id: str, db: Session = Depends(get_db)) -> ScanDetailsResponse:
    scan = db.execute(
        select(Scan)
        .where(Scan.scan_id == scan_id)
        .options(
            selectinload(Scan.project),
            selectinload(Scan.tool_reports),
            selectinload(Scan.findings),
            selectinload(Scan.notifications),
            selectinload(Scan.audit_logs),
        )
    ).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return _scan_details_response(scan)


@router.get("/{scan_id}/audit", response_model=list[AuditLogResponse], summary="Get scan audit history")
def get_scan_audit(scan_id: str, db: Session = Depends(get_db)) -> list[AuditLog]:
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return list(db.execute(select(AuditLog).where(AuditLog.scan_pk == scan.id).order_by(AuditLog.created_at.desc())).scalars().all())
