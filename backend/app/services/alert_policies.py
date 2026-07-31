from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.scan import Alert, Project, ProjectAlertPolicy, Scan
from app.services.repository import normalize_repository_url

SEVERITY_RANK = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
DEFAULT_DASHBOARD_CHANNEL = "dashboard"


def normalize_severity(value: str | None, fallback: str = "LOW") -> str:
    severity = str(value or fallback).upper()
    return severity if severity in SEVERITY_RANK else fallback


def severity_allows(severity: str, minimum: str) -> bool:
    return SEVERITY_RANK.get(normalize_severity(severity, "INFO"), 0) >= SEVERITY_RANK.get(normalize_severity(minimum), 1)


def default_channels_for_severity(severity: str) -> list[str]:
    channels = [DEFAULT_DASHBOARD_CHANNEL, "slack"]
    if severity_allows(severity, "HIGH"):
        channels.append("email")
    return channels


def project_policy_response(project: Project, policy: ProjectAlertPolicy | None = None) -> dict:
    return {
        "project_key": project.project_key,
        "project_name": project.name,
        "repository_url": project.repository_url,
        "enabled": bool(policy.enabled) if policy else False,
        "slack_enabled": bool(policy.slack_enabled) if policy else True,
        "email_enabled": bool(policy.email_enabled) if policy else True,
        "slack_min_severity": normalize_severity(policy.slack_min_severity if policy else "LOW"),
        "email_min_severity": normalize_severity(policy.email_min_severity if policy else "HIGH"),
        "updated_at": policy.updated_at if policy else None,
    }


def policy_for_project(db: Session, project: Project | None) -> ProjectAlertPolicy | None:
    if not project:
        return None
    return db.execute(select(ProjectAlertPolicy).where(ProjectAlertPolicy.project_id == project.id)).scalar_one_or_none()


def project_for_scan(db: Session, scan: Scan) -> Project | None:
    if scan.project_id:
        project = db.execute(select(Project).where(Project.id == scan.project_id)).scalar_one_or_none()
        if project:
            return project
    normalized_repo = normalize_repository_url(scan.repository_url)
    return db.execute(
        select(Project).where(or_(Project.name == scan.project_name, Project.repository_url == normalized_repo))
    ).scalar_one_or_none()


def project_for_alert(db: Session, alert: Alert) -> Project | None:
    normalized_repo = normalize_repository_url(alert.repository or "") if alert.repository else None
    clauses = [Project.name == alert.project_name]
    if normalized_repo:
        clauses.append(Project.repository_url == normalized_repo)
    return db.execute(select(Project).where(or_(*clauses))).scalar_one_or_none()


def channels_for_policy(severity: str, policy: ProjectAlertPolicy | None) -> list[str]:
    if not policy or not policy.enabled:
        return default_channels_for_severity(severity)
    channels = [DEFAULT_DASHBOARD_CHANNEL]
    if policy.slack_enabled and severity_allows(severity, policy.slack_min_severity):
        channels.append("slack")
    if policy.email_enabled and severity_allows(severity, policy.email_min_severity):
        channels.append("email")
    return channels


def channels_for_scan(db: Session, scan: Scan, severity: str) -> list[str]:
    return channels_for_policy(severity, policy_for_project(db, project_for_scan(db, scan)))


def channels_for_alert(db: Session, alert: Alert, severity: str) -> list[str]:
    return channels_for_policy(severity, policy_for_project(db, project_for_alert(db, alert)))
