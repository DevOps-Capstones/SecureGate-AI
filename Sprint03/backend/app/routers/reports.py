from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.database import get_db
from app.models.scan import Finding, Report, Scan
from app.schemas.reports import MasterReportResponse, ReportHistoryResponse
from app.services.master_report import build_master_report, persist_master_report
from app.services.report_export import generate_docx, generate_pdf
from app.services.security_gate import evaluate_scan

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _load_scan(db: Session, scan_id: str) -> Scan:
    scan = db.execute(
        select(Scan).where(Scan.scan_id == scan_id).options(selectinload(Scan.findings))
    ).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


def _master_payload(db: Session, scan: Scan) -> dict:
    master = db.execute(
        select(Report).where(Report.scan_pk == scan.id, Report.report_type == "MASTER")
    ).scalar_one_or_none()
    if master:
        return master.payload

    evaluation = evaluate_scan(scan, scan.findings)
    if scan.status != "COMPLETED" and evaluation["decision"] == "APPROVED":
        scan.deployment_decision = "PENDING"
        evaluation["decision"] = "PENDING"
        evaluation["rejected_reasons"] = ["Awaiting all required tool reports."]
    payload = build_master_report(scan, scan.findings, evaluation)
    persist_master_report(db, scan, payload)
    db.commit()
    return payload


def _record_export(db: Session, scan: Scan, report_type: str, filename: str, payload: dict) -> None:
    report = db.execute(
        select(Report).where(Report.scan_pk == scan.id, Report.report_type == report_type)
    ).scalar_one_or_none()
    if report:
        report.file_path = filename
        report.payload = payload
        report.created_at = datetime.now(timezone.utc)
    else:
        db.add(Report(scan_pk=scan.id, report_type=report_type, file_path=filename, payload=payload))
    db.commit()


@router.get(
    "",
    response_model=list[ReportHistoryResponse],
    summary="List report history",
    description="Lists reports from the last 12 months with project, branch, date, decision, and severity filters.",
)
def list_reports(
    project: str | None = None,
    branch: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    decision: Literal["APPROVED", "REJECTED", "PENDING"] | None = None,
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ReportHistoryResponse]:
    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc) if date_from else datetime.now(timezone.utc) - timedelta(days=365)
    query = select(Report, Scan).join(Scan, Report.scan_pk == Scan.id).where(Report.created_at >= start)
    if date_to:
        query = query.where(Report.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    if project:
        query = query.where(Scan.project_name.ilike(f"%{project}%"))
    if branch:
        query = query.where(Scan.branch == branch)
    if decision:
        query = query.where(Scan.deployment_decision == decision)
    if severity:
        query = query.where(exists().where(Finding.scan_pk == Scan.id, Finding.severity == severity))
    rows = db.execute(query.order_by(Report.created_at.desc()).limit(limit)).all()
    response = []
    for report, scan in rows:
        counts = dict(db.execute(
            select(Finding.severity, func.count(Finding.id)).where(Finding.scan_pk == scan.id).group_by(Finding.severity)
        ).all())
        response.append(ReportHistoryResponse(
            scan_id=scan.scan_id,
            project_name=scan.project_name,
            branch=scan.branch,
            report_type=report.report_type,
            decision=scan.deployment_decision,
            security_score=scan.security_score,
            critical_count=counts.get("CRITICAL", 0),
            high_count=counts.get("HIGH", 0),
            created_at=report.created_at,
        ))
    return response


@router.get("/{scan_id}/json", response_model=MasterReportResponse, summary="Export master report as JSON")
def export_json(scan_id: str, db: Session = Depends(get_db)) -> MasterReportResponse:
    scan = _load_scan(db, scan_id)
    payload = _master_payload(db, scan)
    _record_export(db, scan, "JSON", "deployment_approval.json", payload)
    return MasterReportResponse(**payload)


@router.get("/{scan_id}/pdf", summary="Export master report as PDF")
def export_pdf(scan_id: str, db: Session = Depends(get_db)) -> Response:
    scan = _load_scan(db, scan_id)
    payload = _master_payload(db, scan)
    content = generate_pdf(payload)
    _record_export(db, scan, "PDF", "deployment_approval.pdf", payload)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="deployment_approval.pdf"'},
    )


@router.get("/{scan_id}/docx", summary="Export master report as DOCX")
def export_docx(scan_id: str, db: Session = Depends(get_db)) -> Response:
    scan = _load_scan(db, scan_id)
    payload = _master_payload(db, scan)
    content = generate_docx(payload)
    _record_export(db, scan, "DOCX", "deployment_approval.docx", payload)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="deployment_approval.docx"'},
    )
