from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config.settings import settings
from app.models.database import get_db
from app.models.scan import AuditLog, Report, Scan
from app.services.ai_engine import build_ai_insights, build_remediation_payload, call_ollama, chat_prompt, remediation_context_text, scan_context
from app.services.ai_reports import generate_ai_summary_pdf, generate_remediation_pdf
from app.services.storage import save_binary_report, stored_report_path

router = APIRouter(prefix="/api/v1/ai", tags=["ai"] )


class AIChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=800, examples=["Why was deployment rejected?"])


class AIChatResponse(BaseModel):
    scan_id: str
    answer: str
    model: str
    ollama_status: str


def load_scan(db: Session, scan_id: str) -> Scan:
    scan = db.execute(
        select(Scan)
        .where(Scan.scan_id == scan_id)
        .options(selectinload(Scan.findings), selectinload(Scan.tool_reports), selectinload(Scan.reports))
    ).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


def record_pdf(db: Session, scan: Scan, report_type: str, file_path: str, payload: dict) -> None:
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
    db.add(AuditLog(scan_pk=scan.id, action="AI_REPORT_EXPORTED", message=f"{report_type} requested.", actor="user", log_metadata={"file_path": file_path}))
    db.commit()


@router.get("/scans/{scan_id}/insights", summary="Generate AI insight summary for a scan")
def ai_insights(scan_id: str, db: Session = Depends(get_db)) -> dict:
    scan = load_scan(db, scan_id)
    return build_ai_insights(db, scan)


@router.post("/scans/{scan_id}/chat", response_model=AIChatResponse, summary="Ask AI assistant about the latest scan context")
def ai_chat(scan_id: str, payload: AIChatRequest, db: Session = Depends(get_db)) -> AIChatResponse:
    scan = load_scan(db, scan_id)
    context = scan_context(db, scan)
    remediation_plan = build_remediation_payload(db, scan)
    context["remediation_context"] = remediation_context_text(remediation_plan)
    db.add(AuditLog(scan_pk=scan.id, action="AI_CHAT_REQUEST", message="AI chat question received.", actor="user", log_metadata={"model": settings.ollama_model}))
    answer, ollama_status = call_ollama(chat_prompt(context, payload.question))
    if not answer:
        counts = context["severity_counts"]
        answer = (
            f"Ollama is not available right now. Based on stored scan data, {scan.project_name} is {scan.deployment_decision} "
            f"with score {scan.security_score}/100, {counts['CRITICAL']} critical, {counts['HIGH']} high, "
            f"{counts['MEDIUM']} medium, and {counts['LOW']} low findings. Check the project findings and tool reports for exact files."
        )
    db.add(AuditLog(scan_pk=scan.id, action="AI_CHAT_RESPONSE", message=f"AI chat response status: {ollama_status}.", actor="system", log_metadata={"model": settings.ollama_model, "ollama_status": ollama_status}))
    db.commit()
    return AIChatResponse(scan_id=scan.scan_id, answer=answer, model=settings.ollama_model, ollama_status=ollama_status)


@router.get("/scans/{scan_id}/remediation-plan", summary="Get AI remediation plan JSON")
def ai_remediation_plan(scan_id: str, refresh: bool = Query(default=False), db: Session = Depends(get_db)) -> dict:
    scan = load_scan(db, scan_id)
    return build_remediation_payload(db, scan, refresh=True if refresh else False)


@router.get("/scans/{scan_id}/summary-report/pdf", summary="Download AI summary report PDF")
def ai_summary_pdf(scan_id: str, db: Session = Depends(get_db)) -> FileResponse:
    scan = load_scan(db, scan_id)
    payload = build_ai_insights(db, scan)
    path = stored_report_path(scan.scan_id, "AI_SUMMARY_PDF")
    saved = save_binary_report(scan.scan_id, "AI_SUMMARY_PDF", generate_ai_summary_pdf(payload))
    record_pdf(db, scan, "AI_SUMMARY_PDF", saved, payload)
    return FileResponse(path, media_type="application/pdf", filename="AI_Summary_Report.pdf")


@router.get("/scans/{scan_id}/remediation-plan/pdf", summary="Download AI remediation plan PDF")
def ai_remediation_pdf(scan_id: str, db: Session = Depends(get_db)) -> FileResponse:
    scan = load_scan(db, scan_id)
    payload = build_remediation_payload(db, scan, refresh=True)
    path = stored_report_path(scan.scan_id, "AI_REMEDIATION_PDF")
    saved = save_binary_report(scan.scan_id, "AI_REMEDIATION_PDF", generate_remediation_pdf(payload))
    record_pdf(db, scan, "AI_REMEDIATION_PDF", saved, payload)
    return FileResponse(path, media_type="application/pdf", filename=f"{scan.scan_id}_AI_Remediation_Plan.pdf")
