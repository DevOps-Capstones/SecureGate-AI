from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.scan import AuditLog, Finding, Notification, Project, Report, Scan, ToolReport
from app.services.gitleaks import normalize_gitleaks_report
from app.services.lifecycle import set_scan_status, utcnow
from app.services.master_report import build_master_report, persist_master_report
from app.services.projects import build_project_findings, get_or_create_project, load_project
from app.services.notifications import send_scan_notifications
from app.services.alerts import create_alert, evaluate_scan_alerts
from app.services.report_export import generate_docx, generate_pdf
from app.services.repository import normalize_repository_url
from app.services.scan_id import generate_scan_id
from app.services.security_gate import evaluate_scan
from app.services.sonarqube import extract_quality_gate_status, normalize_sonarqube_report
from app.services.semgrep import normalize_semgrep_report
from app.services.unit_tests import normalize_unit_tests_report
from app.services.storage import save_binary_report, save_json_report
from app.services.trivy import normalize_trivy_report

REQUIRED_TOOLS = {"gitleaks", "semgrep", "trivy-fs", "trivy-image", "sonarqube", "unit-tests"}

def _extract_image_details(payload: dict | list) -> tuple[str | None, str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None, None
    artifact = str(payload.get("ArtifactName") or payload.get("Target") or "").strip()
    if not artifact:
        return None, None, None
    if ":" in artifact and "/" not in artifact.rsplit(":", 1)[-1]:
        image, tag = artifact.rsplit(":", 1)
        return image, tag, artifact
    return artifact, None, artifact


TOOL_NORMALIZERS = {
    "gitleaks": normalize_gitleaks_report,
    "trivy-fs": lambda payload: normalize_trivy_report(payload, "trivy-fs"),
    "trivy-image": lambda payload: normalize_trivy_report(payload, "trivy-image"),
    "semgrep": normalize_semgrep_report,
    "sonarqube": normalize_sonarqube_report,
    "unit-tests": normalize_unit_tests_report,
}


def _audit(db: Session, scan: Scan | None, action: str, message: str, metadata: dict | None = None, actor: str = "system") -> None:
    db.add(
        AuditLog(
            scan_pk=scan.id if scan else None,
            action=action,
            message=message,
            actor=actor,
            log_metadata=metadata or {},
        )
    )


def create_scan_record(
    db: Session,
    project_name: str,
    repository_url: str,
    branch: str,
    commit_sha: str,
    pipeline_run_id: str | None = None,
    actor: str = "manual",
) -> Scan:
    normalized_url = normalize_repository_url(repository_url)
    project = get_or_create_project(db, project_name, normalized_url)

    scan = Scan(
        scan_id=generate_scan_id(db),
        project_id=project.id,
        project_name=project.name,
        repository_url=project.repository_url,
        branch=branch,
        commit_sha=commit_sha,
        pipeline_run_id=pipeline_run_id,
        pipeline_status="STARTED" if pipeline_run_id else None,
        status="RECEIVED",
        received_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.flush()
    _audit(db, scan, "SCAN_RECEIVED", "Scan metadata received from CI pipeline.", {"pipeline_run_id": pipeline_run_id}, actor)
    db.commit()
    db.refresh(scan)
    return scan


def ingest_tool_report(db: Session, scan_id: str, tool_name: str, payload: dict | list, actor: str = "github-actions") -> tuple[Scan, ToolReport, list[Finding]]:
    scan = db.execute(
        select(Scan).where(Scan.scan_id == scan_id).options(selectinload(Scan.tool_reports))
    ).scalar_one_or_none()
    if not scan:
        raise LookupError("Scan not found")

    normalizer = TOOL_NORMALIZERS[tool_name]
    set_scan_status(db, scan, "PROCESSING", "Tool report upload received.", {"tool": tool_name}, actor)
    db.flush()

    try:
        previous_reports = db.execute(
            select(ToolReport.id).where(ToolReport.scan_pk == scan.id, ToolReport.tool_name == tool_name)
        ).scalars().all()
        if previous_reports:
            db.execute(delete(Finding).where(Finding.tool_report_pk.in_(previous_reports)))
            db.execute(delete(ToolReport).where(ToolReport.id.in_(previous_reports)))
            db.flush()

        file_path = save_json_report(scan.scan_id, tool_name, payload)
        normalized_findings = normalizer(payload)
        report = ToolReport(
            scan_pk=scan.id,
            tool_name=tool_name,
            status="UPLOADED",
            raw_payload=payload if isinstance(payload, dict) else {"items": payload},
            file_path=file_path,
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(report)
        db.flush()

        finding_models = []
        for item in normalized_findings:
            finding = Finding(
                scan_pk=scan.id,
                tool_report_pk=report.id,
                tool=item["tool"],
                severity=item["severity"],
                title=item["title"],
                description=item.get("description"),
                file=item.get("file"),
                source_tool=item["source_tool"],
                raw_data=item.get("raw_data", {}),
            )
            db.add(finding)
            finding_models.append(finding)

        if tool_name == "sonarqube" and isinstance(payload, dict):
            scan.sonar_quality_gate = extract_quality_gate_status(payload)
        if tool_name == "trivy-image":
            scan.image_name, scan.image_tag, scan.image_full_path = _extract_image_details(payload)

        uploaded_tools = set(
            db.execute(select(ToolReport.tool_name).where(ToolReport.scan_pk == scan.id)).scalars().all()
        )
        all_findings = list(db.execute(select(Finding).where(Finding.scan_pk == scan.id)).scalars().all())
        set_scan_status(db, scan, "SCORING", "Security score calculation started.", {"uploaded_tools": sorted(uploaded_tools)}, "system")
        evaluation = evaluate_scan(scan, all_findings)

        if REQUIRED_TOOLS.issubset(uploaded_tools):
            set_scan_status(db, scan, "REPORT_GENERATION", "All required reports received; generating master report.", actor="system")
            payload_report = build_master_report(scan, all_findings, evaluation)
            persist_master_report(db, scan, payload_report)
            save_json_report(scan.scan_id, "JSON", payload_report)
            save_binary_report(scan.scan_id, "PDF", generate_pdf(payload_report))
            save_binary_report(scan.scan_id, "DOCX", generate_docx(payload_report))
            generated_alerts = evaluate_scan_alerts(db, scan)
            if generated_alerts:
                _audit(db, scan, "ALERTS_GENERATED", "Sprint 5 monitoring alerts generated for this scan.", {"alerts": [alert.alert_id for alert in generated_alerts]}, "system")
            if scan.notification_sent_at is None:
                notifications = send_scan_notifications(db, scan, payload_report)
                failed_notifications = [item for item in notifications if item.status == "FAILED"]
                if failed_notifications:
                    alert = create_alert(db, scan, "MEDIUM", "NOTIFICATION_DELIVERY_FAILED", "Slack or email delivery failed for this scan.", "Verify Slack webhook and SMTP settings, then resend the notification if needed.")
                    _audit(db, scan, "ALERTS_GENERATED", "Notification delivery failure alert generated.", {"alert": alert.alert_id}, "system")
                set_scan_status(
                    db,
                    scan,
                    "NOTIFICATION_SENT",
                    "Deployment decision notifications processed.",
                    {"notifications": [item.status for item in notifications]},
                    "system",
                )
            else:
                _audit(db, scan, "NOTIFICATION_SKIPPED", "Notifications already sent for this scan; duplicate delivery skipped.", actor="system")
            set_scan_status(db, scan, "COMPLETED", "Scan workflow completed.", actor="system")
        else:
            scan.status = "PROCESSING"
            scan.completed_at = None
            if evaluation["decision"] == "APPROVED":
                scan.deployment_decision = "PENDING"
        _audit(
            db,
            scan,
            "REPORT_UPLOADED",
            f"{tool_name} report uploaded, stored, and normalized.",
            {"tool": tool_name, "findings_count": len(finding_models), "file_path": file_path},
            actor,
        )
        db.commit()
        db.refresh(scan)
        db.refresh(report)
        return scan, report, finding_models
    except Exception as exc:
        db.rollback()
        failed_scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalar_one()
        set_scan_status(db, failed_scan, "FAILED", str(exc), {"tool": tool_name}, "system")
        if tool_name in REQUIRED_TOOLS:
            create_alert(db, failed_scan, "MEDIUM", "REPORT_GENERATION_FAILED", "Master security report generation or scan finalization failed.", "Check report generation logs, storage permissions, and uploaded report payloads.")
            _audit(db, failed_scan, "ALERTS_GENERATED", "Report generation failure alert generated.", {"tool": tool_name, "error": str(exc)}, "system")
        db.commit()
        raise


def complete_pipeline(db: Session, scan_id: str, status: str) -> Scan:
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalar_one_or_none()
    if not scan:
        raise LookupError("Scan not found")
    normalized_status = status.upper()
    scan.pipeline_status = normalized_status
    if normalized_status == "FAILED":
        set_scan_status(db, scan, "FAILED", "CI pipeline reported failure.", {"pipeline_status": normalized_status}, "github-actions")
    else:
        _audit(db, scan, "PIPELINE_COMPLETED", "CI pipeline reported completion.", {"pipeline_status": normalized_status}, "github-actions")
        if scan.status not in {"COMPLETED", "FAILED"}:
            scan.completed_at = utcnow()
    db.commit()
    db.refresh(scan)
    return scan


def get_dashboard_summary(db: Session) -> dict:
    total_projects = db.execute(select(func.count(Project.id))).scalar_one()
    latest_project_scan = db.execute(select(Scan).order_by(Scan.received_at.desc()).limit(1)).scalar_one_or_none()
    active_project = None
    if latest_project_scan and latest_project_scan.project_id:
        active_project = db.execute(select(Project).where(Project.id == latest_project_scan.project_id)).scalar_one_or_none()
    active_project_id = active_project.id if active_project else (latest_project_scan.project_id if latest_project_scan else None)
    active_project_name = active_project.name if active_project else (latest_project_scan.project_name if latest_project_scan else None)
    active_repository_url = active_project.repository_url if active_project else (latest_project_scan.repository_url if latest_project_scan else None)
    project_filter = Scan.project_id == active_project_id if active_project_id else None
    active_scan_ids = []
    if active_project_id:
        active_scan_ids = db.execute(select(Scan.id).where(Scan.project_id == active_project_id)).scalars().all()
    total_scans_query = select(func.count(Scan.id))
    active_scans_query = select(func.count(Scan.id)).where(Scan.status.in_(["RECEIVED", "PROCESSING", "SCORING", "REPORT_GENERATION", "NOTIFICATION_SENT"]))
    recent_scans_query = select(Scan).order_by(Scan.received_at.desc()).limit(60)
    if project_filter is not None:
        total_scans_query = total_scans_query.where(project_filter)
        active_scans_query = active_scans_query.where(project_filter)
        recent_scans_query = select(Scan).where(project_filter).order_by(Scan.received_at.desc()).limit(60)
    total_scans = db.execute(total_scans_query).scalar_one()
    active_scans = db.execute(active_scans_query).scalar_one()
    recent_scans = db.execute(recent_scans_query).scalars().all()
    latest_upload_query = (
        select(ToolReport, Scan)
        .join(Scan, ToolReport.scan_pk == Scan.id)
        .order_by(ToolReport.uploaded_at.desc())
        .limit(60)
    )
    if project_filter is not None:
        latest_upload_query = latest_upload_query.where(project_filter)
    latest_upload_rows = db.execute(latest_upload_query).all()
    finding_query = select(Finding).order_by(Finding.created_at.desc()).limit(60)
    if active_scan_ids:
        finding_query = finding_query.where(Finding.scan_pk.in_(active_scan_ids))
    recent_findings = db.execute(finding_query).scalars().all()
    recent_notifications = db.execute(select(Notification).order_by(Notification.created_at.desc()).limit(60)).scalars().all()
    report_query = (
        select(Report, Scan)
        .join(Scan, Report.scan_pk == Scan.id)
        .where(Report.report_type == "MASTER")
        .order_by(Report.created_at.desc())
        .limit(60)
    )
    if project_filter is not None:
        report_query = report_query.where(project_filter)
    report_rows = db.execute(report_query).all()
    evaluated_query = select(Scan).where(Scan.security_score.is_not(None)).order_by(Scan.evaluated_at.desc()).limit(60)
    if project_filter is not None:
        evaluated_query = evaluated_query.where(project_filter)
    evaluated_scans = db.execute(evaluated_query).scalars().all()
    latest_evaluated = evaluated_scans[0] if evaluated_scans else None
    project_findings = []
    if active_project:
        loaded_project = load_project(db, active_project.project_key)
        project_findings = build_project_findings(loaded_project) if loaded_project else []
    open_project_findings = [item for item in project_findings if item["resolution_status"] == "OPEN"]
    project_severity_counts = Counter(item["severity"] for item in open_project_findings)
    project_status_counts = Counter(item["resolution_status"] for item in project_findings)
    critical_findings = project_severity_counts.get("CRITICAL", 0)
    high_findings = project_severity_counts.get("HIGH", 0)
    medium_findings = project_severity_counts.get("MEDIUM", 0)
    low_findings = project_severity_counts.get("LOW", 0)
    pending_findings = project_status_counts.get("OPEN", 0) + project_status_counts.get("PENDING_RECHECK", 0)
    resolved_findings = project_status_counts.get("RESOLVED", 0)
    trend_query = select(Scan).where(Scan.security_score.is_not(None)).options(selectinload(Scan.findings)).order_by(Scan.evaluated_at.desc()).limit(60)
    if project_filter is not None:
        trend_query = trend_query.where(project_filter)
    trend_scans = db.execute(trend_query).scalars().all()
    vulnerability_trend = []
    for item in reversed(trend_scans):
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "PENDING": 0, "RESOLVED": 0}
        for finding in item.findings:
            severity = finding.severity.upper()
            if severity in counts:
                counts[severity] += 1
            if finding.resolution_status == "RESOLVED":
                counts["RESOLVED"] += 1
            else:
                counts["PENDING"] += 1
        vulnerability_trend.append({"scan_id": item.scan_id, "project_name": item.project_name, "evaluated_at": item.evaluated_at, **counts})
    return {
        "total_projects": total_projects,
        "active_project_name": active_project_name,
        "active_project_key": active_project.project_key if active_project else None,
        "active_repository_url": active_repository_url,
        "total_scans": total_scans,
        "active_scans": active_scans,
        "recent_scans": recent_scans,
        "latest_uploads": [
            {
                "tool_name": report.tool_name,
                "status": report.status,
                "uploaded_at": report.uploaded_at,
                "file_path": report.file_path,
                "scan_id": scan.scan_id,
            }
            for report, scan in latest_upload_rows
        ],
        "most_recent_findings": recent_findings,
        "latest_security_score": latest_evaluated.security_score if latest_evaluated else None,
        "latest_approval_status": latest_evaluated.deployment_decision if latest_evaluated else "PENDING",
        "critical_findings": critical_findings,
        "high_findings": high_findings,
        "medium_findings": medium_findings,
        "low_findings": low_findings,
        "pending_findings": pending_findings,
        "resolved_findings": resolved_findings,
        "vulnerability_trend": vulnerability_trend,
        "score_trend": [
            {"scan_id": scan.scan_id, "score": scan.security_score, "evaluated_at": scan.evaluated_at}
            for scan in reversed(evaluated_scans)
        ],
        "recent_reports": [
            {
                "scan_id": scan.scan_id,
                "project_name": scan.project_name,
                "report_type": report.report_type,
                "file_path": report.file_path,
                "created_at": report.created_at,
                "image_full_path": scan.image_full_path,
            }
            for report, scan in report_rows
        ],
        "recent_notifications": recent_notifications,
    }
