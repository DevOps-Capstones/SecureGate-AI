from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.database import get_db
from app.models.scan import AuditLog, Finding, Report, Scan
from app.schemas.reports import ReportHistoryResponse
from app.services.lifecycle import set_scan_status
from app.services.master_report import build_master_report, persist_master_report
from app.services.report_export import generate_docx, generate_pdf
from app.services.security_gate import evaluate_scan
from app.services.storage import save_binary_report, save_json_report, stored_report_path

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _load_scan(db: Session, scan_id: str) -> Scan:
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id).options(selectinload(Scan.findings), selectinload(Scan.tool_reports))).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


def _master_payload(db: Session, scan: Scan, force_rebuild: bool = False) -> dict:
    master = db.execute(
        select(Report)
        .where(Report.scan_pk == scan.id, Report.report_type == "MASTER")
        .order_by(Report.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if master and not force_rebuild:
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


def _record_export(db: Session, scan: Scan, report_type: str, file_path: str, payload: dict) -> None:
    report = db.execute(
        select(Report)
        .where(Report.scan_pk == scan.id, Report.report_type == report_type)
        .order_by(Report.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if report:
        report.file_path = file_path
        report.payload = payload
        report.created_at = datetime.now(timezone.utc)
    else:
        db.add(Report(scan_pk=scan.id, report_type=report_type, file_path=file_path, payload=payload))
    db.add(AuditLog(scan_pk=scan.id, action="REPORT_EXPORTED", message=f"{report_type} report requested.", actor="user", log_metadata={"file_path": file_path}))
    db.commit()


def _ensure_export_file(db: Session, scan: Scan, report_type: Literal["PDF", "DOCX", "JSON"], refresh: bool = False) -> Path:
    path = stored_report_path(scan.scan_id, report_type)
    payload = _master_payload(db, scan, force_rebuild=refresh)
    if refresh or not path.exists():
        if scan.status not in {"COMPLETED", "FAILED"}:
            set_scan_status(db, scan, "REPORT_GENERATION", f"Generating stored {report_type} report export.", {"report_type": report_type})
        else:
            db.add(AuditLog(scan_pk=scan.id, action="REPORT_GENERATION", message=f"Generating stored {report_type} report export.", actor="system", log_metadata={"report_type": report_type}))
        if report_type == "PDF":
            saved = save_binary_report(scan.scan_id, report_type, generate_pdf(payload))
        elif report_type == "DOCX":
            saved = save_binary_report(scan.scan_id, report_type, generate_docx(payload))
        else:
            saved = save_json_report(scan.scan_id, report_type, payload)
        _record_export(db, scan, report_type, saved, payload)
    else:
        _record_export(db, scan, report_type, str(path), payload)
    return path


@router.get("", response_model=list[ReportHistoryResponse], summary="List report history")
def list_reports(
    project: str | None = None,
    branch: str | None = None,
    image: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    decision: Literal["APPROVED", "REJECTED", "PENDING"] | None = None,
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None,
    score_min: int | None = Query(default=None, ge=0, le=100),
    score_max: int | None = Query(default=None, ge=0, le=100),
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
    if image:
        query = query.where((Scan.image_name.ilike(f"%{image}%")) | (Scan.image_full_path.ilike(f"%{image}%")))
    if decision:
        query = query.where(Scan.deployment_decision == decision)
    if severity:
        query = query.where(exists().where(Finding.scan_pk == Scan.id, Finding.severity == severity))
    if score_min is not None:
        query = query.where(Scan.security_score >= score_min)
    if score_max is not None:
        query = query.where(Scan.security_score <= score_max)
    rows = db.execute(query.order_by(Report.created_at.desc()).limit(limit)).all()
    response = []
    for report, scan in rows:
        counts = dict(db.execute(select(Finding.severity, func.count(Finding.id)).where(Finding.scan_pk == scan.id).group_by(Finding.severity)).all())
        response.append(ReportHistoryResponse(
            scan_id=scan.scan_id,
            project_name=scan.project_name,
            branch=scan.branch,
            image_name=scan.image_name,
            image_tag=scan.image_tag,
            image_full_path=scan.image_full_path,
            report_type=report.report_type,
            decision=scan.deployment_decision,
            security_score=scan.security_score,
            critical_count=counts.get("CRITICAL", 0),
            high_count=counts.get("HIGH", 0),
            created_at=report.created_at,
        ))
    return response


def _delete_report_type(db: Session, scan: Scan, report_type: str) -> int:
    normalized_type = report_type.upper()
    reports = [report for report in scan.reports if report.report_type.upper() == normalized_type]
    for report in reports:
        if report.file_path:
            path = Path(report.file_path)
            if not path.is_absolute():
                path = Path.cwd() / report.file_path
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        db.delete(report)
    return len(reports)


@router.post("/{scan_id}/generate", summary="Generate missing master report exports")
def generate_master_exports(scan_id: str, db: Session = Depends(get_db)) -> dict:
    scan = _load_scan(db, scan_id)
    generated = []
    for report_type in ("JSON", "PDF", "DOCX"):
        _ensure_export_file(db, scan, report_type, refresh=True)
        generated.append(report_type)
    return {"scan_id": scan.scan_id, "status": "GENERATED", "reports": generated}


@router.delete("/{scan_id}/{report_type}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete one stored report export")
def delete_report_export(scan_id: str, report_type: Literal["MASTER", "PDF", "DOCX", "JSON", "AI_SUMMARY", "AI_SUMMARY_PDF", "AI_REMEDIATION", "AI_REMEDIATION_PDF"], db: Session = Depends(get_db)) -> Response:
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id).options(selectinload(Scan.reports))).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    deleted = _delete_report_type(db, scan, report_type)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    db.add(AuditLog(scan_pk=scan.id, action="REPORT_DELETED", message=f"{report_type} report export was deleted by user.", actor="user", log_metadata={"report_type": report_type, "deleted_reports": deleted}))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete stored master report metadata for a scan")
def delete_report(scan_id: str, db: Session = Depends(get_db)) -> Response:
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id).options(selectinload(Scan.reports))).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    deleted = _delete_report_type(db, scan, "MASTER")
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master report not found")
    db.add(AuditLog(scan_pk=scan.id, action="REPORT_DELETED", message="Master report metadata was deleted by user.", actor="user", log_metadata={"report_type": "MASTER", "deleted_reports": deleted}))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{scan_id}/status", summary="Check master report export availability")
def report_status(scan_id: str, db: Session = Depends(get_db)) -> dict:
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id).options(selectinload(Scan.reports))).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    report_types = {report.report_type.upper() for report in scan.reports}
    return {
        "scan_id": scan.scan_id,
        "has_master_report": "MASTER" in report_types,
        "exports": {
            "PDF": "PDF" in report_types or stored_report_path(scan.scan_id, "PDF").exists(),
            "DOCX": "DOCX" in report_types or stored_report_path(scan.scan_id, "DOCX").exists(),
            "JSON": "JSON" in report_types or stored_report_path(scan.scan_id, "JSON").exists(),
            "AI_SUMMARY_PDF": "AI_SUMMARY_PDF" in report_types or stored_report_path(scan.scan_id, "AI_SUMMARY_PDF").exists(),
            "AI_REMEDIATION_PDF": "AI_REMEDIATION_PDF" in report_types or stored_report_path(scan.scan_id, "AI_REMEDIATION_PDF").exists(),
        },
    }


@router.get("/{scan_id}/json", summary="Export stored master report as JSON")
def export_json(scan_id: str, refresh: bool = Query(default=False), db: Session = Depends(get_db)) -> FileResponse:
    scan = _load_scan(db, scan_id)
    path = _ensure_export_file(db, scan, "JSON", refresh)
    return FileResponse(path, media_type="application/json", filename="deployment_approval.json")


@router.get("/{scan_id}/pdf", summary="Export stored master report as PDF")
def export_pdf(scan_id: str, refresh: bool = Query(default=True), db: Session = Depends(get_db)) -> FileResponse:
    scan = _load_scan(db, scan_id)
    path = _ensure_export_file(db, scan, "PDF", refresh)
    return FileResponse(path, media_type="application/pdf", filename="deployment_approval.pdf")


@router.get("/{scan_id}/docx", summary="Export stored master report as DOCX")
def export_docx(scan_id: str, refresh: bool = Query(default=True), db: Session = Depends(get_db)) -> FileResponse:
    scan = _load_scan(db, scan_id)
    path = _ensure_export_file(db, scan, "DOCX", refresh)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename="deployment_approval.docx")
