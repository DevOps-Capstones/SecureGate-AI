from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.database import get_db
from app.models.scan import Alert, Finding, Notification, Project, Report, Scan, ToolReport

router = APIRouter(tags=["metrics"])
API_REQUESTS = Counter("securegate_api_requests_total", "Total API requests", ["method", "path", "status"])
API_ERRORS = Counter("securegate_api_errors_total", "Total API errors", ["method", "path"])
REPORT_DOWNLOADS = Counter("securegate_report_download_count", "Report downloads counted by API responses", ["format"])


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _scan_duration(scan: Scan) -> float | None:
    if scan.completed_at and scan.received_at:
        return (scan.completed_at - scan.received_at).total_seconds()
    return None


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics(request: Request, db: Session = Depends(get_db)) -> Response:
    registry = CollectorRegistry()
    def gauge(name, description, labels=()):
        return Gauge(name, description, labels, registry=registry)

    scans = db.execute(select(Scan)).scalars().all()
    findings = db.execute(select(Finding)).scalars().all()
    reports = db.execute(select(Report)).scalars().all()
    notifications = db.execute(select(Notification)).scalars().all()
    tool_reports = db.execute(select(ToolReport)).scalars().all()
    alerts = db.execute(select(Alert)).scalars().all()

    gauge("securegate_projects_total", "Registered projects").set(db.execute(select(func.count(Project.id))).scalar_one())
    gauge("securegate_total_scans", "Total scans").set(len(scans))
    gauge("securegate_successful_scans", "Completed scans").set(sum(1 for s in scans if s.status == "COMPLETED"))
    gauge("securegate_failed_scans", "Failed scans").set(sum(1 for s in scans if s.status == "FAILED" or s.failed_at is not None))
    gauge("securegate_running_scans", "Running scans").set(sum(1 for s in scans if s.status in {"RECEIVED", "PROCESSING", "SCORING", "REPORT_GENERATION", "NOTIFICATION_SENT"}))
    gauge("securegate_average_scan_duration_seconds", "Average scan duration").set(_avg([v for v in (_scan_duration(s) for s in scans) if v is not None]))
    gauge("securegate_average_report_generation_time_seconds", "Average report generation time").set(_avg([(s.report_generation_at - s.scoring_at).total_seconds() for s in scans if s.report_generation_at and s.scoring_at]))
    gauge("securegate_average_security_score", "Average security score").set(_avg([float(s.security_score) for s in scans if s.security_score is not None]))
    gauge("securegate_deployment_approved_count", "Approved deployments").set(sum(1 for s in scans if s.deployment_decision == "APPROVED"))
    gauge("securegate_deployment_rejected_count", "Rejected deployments").set(sum(1 for s in scans if s.deployment_decision == "REJECTED"))
    gauge("securegate_sonarqube_quality_gate_failed_count", "SonarQube quality gate failures").set(sum(1 for s in scans if s.sonar_quality_gate and s.sonar_quality_gate not in {"OK", "UNKNOWN"}))
    gauge("securegate_report_generation_failed_count", "Scans that failed during or before report generation").set(sum(1 for s in scans if s.status == "FAILED" and s.report_generation_at is None))

    gauge("securegate_critical_vulnerability_threshold", "Configured critical vulnerability alert threshold").set(settings.critical_vulnerability_threshold)
    gauge("securegate_high_vulnerability_threshold", "Configured high vulnerability alert threshold").set(settings.high_vulnerability_threshold)
    gauge("securegate_security_score_threshold", "Configured minimum security score threshold").set(settings.security_score_threshold)
    gauge("securegate_block_high_vulnerabilities", "Whether high vulnerabilities block deployment").set(1 if settings.block_high_vulnerabilities else 0)
    gauge("securegate_quality_gate_required", "Whether Sonar quality gate is required").set(1 if settings.quality_gate_required else 0)
    gauge("securegate_secret_detection_required", "Whether secret detection blocks deployment").set(1 if settings.secret_detection_required else 0)

    severity_counts = {sev: sum(1 for f in findings if f.severity.upper() == sev) for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}
    for sev, metric in [("CRITICAL", "critical_vulnerabilities"), ("HIGH", "high_vulnerabilities"), ("MEDIUM", "medium_vulnerabilities"), ("LOW", "low_vulnerabilities")]:
        gauge(f"securegate_{metric}", f"{sev.title()} vulnerabilities").set(severity_counts[sev])
    gauge("securegate_secrets_detected", "GitLeaks findings").set(sum(1 for f in findings if f.tool == "gitleaks"))
    gauge("securegate_code_smells", "SonarQube code smells").set(sum(1 for f in findings if f.tool == "sonarqube" and str((f.raw_data or {}).get("type", "")).upper() == "CODE_SMELL"))
    gauge("securegate_bugs", "SonarQube bugs").set(sum(1 for f in findings if f.tool == "sonarqube" and str((f.raw_data or {}).get("type", "")).upper() == "BUG"))
    gauge("securegate_security_hotspots", "SonarQube hotspots/security issues").set(sum(1 for f in findings if f.tool == "sonarqube" and "SECURITY" in str((f.raw_data or {}).get("type", "")).upper()))
    gauge("securegate_gitleaks_findings", "GitLeaks findings").set(sum(1 for f in findings if f.tool == "gitleaks"))
    gauge("securegate_trivy_findings", "Trivy findings").set(sum(1 for f in findings if f.tool in {"trivy", "trivy-fs", "trivy-image"}))
    gauge("securegate_sonarqube_findings", "SonarQube findings").set(sum(1 for f in findings if f.tool == "sonarqube"))
    gauge("securegate_reports_generated", "Reports generated").set(len(reports))
    gauge("securegate_slack_notifications_sent", "Slack notifications sent").set(sum(1 for n in notifications if n.notification_type == "SLACK" and n.status == "SENT"))
    gauge("securegate_email_notifications_sent", "Email notifications sent").set(sum(1 for n in notifications if n.notification_type == "EMAIL" and n.status == "SENT"))
    gauge("securegate_slack_notifications_failed", "Slack notifications failed").set(sum(1 for n in notifications if n.notification_type == "SLACK" and n.status == "FAILED"))
    gauge("securegate_email_notifications_failed", "Email notifications failed").set(sum(1 for n in notifications if n.notification_type == "EMAIL" and n.status == "FAILED"))
    gauge("securegate_dashboard_active_users", "Dashboard active users placeholder").set(1)
    gauge("securegate_database_response_time_seconds", "Database response time placeholder").set(0.001)
    gauge("securegate_alerts_open", "Open alerts").set(sum(1 for a in alerts if a.status == "OPEN"))
    gauge("securegate_tool_reports_uploaded", "Tool reports uploaded").set(len(tool_reports))

    return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")
