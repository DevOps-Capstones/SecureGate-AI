from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.scan import Finding, Project, Scan, ToolReport
from app.services.repository import normalize_repository_url

EXPECTED_TOOLS = ["gitleaks", "semgrep", "trivy-fs", "sonarqube", "unit-tests", "trivy-image"]
TOOL_LABELS = {"gitleaks": "GitLeaks", "semgrep": "Semgrep", "trivy-fs": "Trivy FS", "trivy-image": "Trivy Image", "sonarqube": "SonarQube", "unit-tests": "Unit Tests"}


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


def _finding_identity(finding: Finding) -> tuple[str, str, str, str]:
    return (
        (finding.tool or "").strip().lower(),
        (finding.severity or "UNKNOWN").strip().upper(),
        " ".join((finding.title or "").strip().lower().split()),
        " ".join((finding.file or "N/A").strip().lower().split()),
    )


def build_project_findings(project: Project, status: str | None = None) -> list[dict]:
    scans = sorted(project.scans, key=lambda scan: scan.received_at)
    latest_scan = scans[-1] if scans else None
    latest_keys = {_finding_identity(finding) for finding in latest_scan.findings} if latest_scan else set()
    grouped: dict[tuple[str, str, str, str], dict] = {}

    for scan in scans:
        for finding in scan.findings:
            key = _finding_identity(finding)
            item = grouped.get(key)
            if item is None:
                item = {
                    "tool": finding.tool,
                    "severity": finding.severity.upper(),
                    "title": finding.title,
                    "description": finding.description,
                    "file": finding.file,
                    "source_tool": finding.source_tool,
                    "first_seen_scan_id": scan.scan_id,
                    "first_seen_at": finding.created_at,
                    "latest_seen_scan_id": scan.scan_id,
                    "latest_seen_at": finding.created_at,
                    "occurrences": 0,
                    "resolution_status": "OPEN",
                    "resolved_at": None,
                }
                grouped[key] = item
            item["latest_seen_scan_id"] = scan.scan_id
            item["latest_seen_at"] = finding.created_at
            item["description"] = item["description"] or finding.description
            item["occurrences"] += 1

    latest_complete = bool(latest_scan and latest_scan.status in {"COMPLETED", "FAILED"})
    for key, item in grouped.items():
        if key in latest_keys:
            item["resolution_status"] = "OPEN"
            item["resolved_at"] = None
        elif latest_complete:
            item["resolution_status"] = "RESOLVED"
            item["resolved_at"] = latest_scan.completed_at or latest_scan.failed_at or latest_scan.received_at if latest_scan else None
        else:
            item["resolution_status"] = "PENDING_RECHECK"
            item["resolved_at"] = None

    requested_status = status.upper() if status else None
    findings = list(grouped.values())
    if requested_status and requested_status != "ALL":
        findings = [item for item in findings if item["resolution_status"] == requested_status]

    return sorted(
        findings,
        key=lambda item: (
            0 if item["resolution_status"] == "OPEN" else 1,
            SEVERITY_ORDER.get(item["severity"], 9),
            str(item["latest_seen_at"]),
        ),
    )


def generate_project_key(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"PRJ-{today}-"
    latest = db.execute(
        select(func.max(func.cast(func.substring(Project.project_key, len(prefix) + 1), Integer)))
        .where(Project.project_key.like(f"{prefix}%"))
    ).scalar_one_or_none() or 0
    next_number = int(latest) + 1
    while True:
        candidate = f"{prefix}{next_number:04d}"
        exists = db.execute(select(Project.id).where(Project.project_key == candidate)).scalar_one_or_none()
        if not exists:
            return candidate
        next_number += 1


def _find_project_by_repository(db: Session, repository_url: str) -> Project | None:
    normalized_url = normalize_repository_url(repository_url)
    return db.execute(
        select(Project).where(func.lower(Project.repository_url) == normalized_url.lower())
    ).scalar_one_or_none()


def _sync_project_repository_url(db: Session, project: Project, repository_url: str) -> Project:
    normalized_url = normalize_repository_url(repository_url)
    if project.repository_url != normalized_url:
        project.repository_url = normalized_url
        db.flush()
    return project


def get_or_create_project(db: Session, name: str, repository_url: str) -> Project:
    normalized_url = normalize_repository_url(repository_url)
    project = _find_project_by_repository(db, normalized_url)
    if project:
        return _sync_project_repository_url(db, project, normalized_url)
    existing_by_name = db.execute(select(Project).where(func.lower(Project.name) == name.lower())).scalar_one_or_none()
    if existing_by_name:
        raise ValueError("Project already exists")
    project = Project(project_key=generate_project_key(db), name=name, repository_url=normalized_url)
    db.add(project)
    db.flush()
    return project


def create_project(db: Session, name: str, repository_url: str) -> Project:
    normalized_url = normalize_repository_url(repository_url)
    existing_by_name = db.execute(select(Project).where(func.lower(Project.name) == name.lower())).scalar_one_or_none()
    if existing_by_name:
        raise ValueError("Project already exists")
    existing_by_repo = _find_project_by_repository(db, normalized_url)
    if existing_by_repo:
        raise ValueError("Project already exists")
    project = Project(project_key=generate_project_key(db), name=name, repository_url=normalized_url)
    db.add(project)
    db.flush()
    return project


def delete_project(db: Session, project_key: str) -> bool:
    project = db.execute(select(Project).where(Project.project_key == project_key)).scalar_one_or_none()
    if not project:
        return False
    db.delete(project)
    db.flush()
    return True


def build_project_health(project: Project) -> dict:
    scans = sorted(project.scans, key=lambda scan: scan.received_at, reverse=True)
    latest = scans[0] if scans else None
    findings = [finding for scan in scans for finding in scan.findings]
    severity_counts = Counter(finding.severity.upper() for finding in findings)
    tool_counts: dict[str, Counter] = defaultdict(Counter)
    for finding in findings:
        tool_counts[finding.tool][finding.severity.upper()] += 1

    latest_reports = {report.tool_name: report for report in latest.tool_reports} if latest else {}
    tool_health = []
    for tool in EXPECTED_TOOLS:
        report = latest_reports.get(tool)
        status = report.status if report else "NOT_UPLOADED"
        if latest and tool == "sonarqube" and report:
            status = f"GATE_{latest.sonar_quality_gate}"
        counts = tool_counts.get(tool, Counter())
        tool_health.append({
            "tool": tool,
            "label": TOOL_LABELS.get(tool, tool),
            "status": status,
            "critical": counts.get("CRITICAL", 0),
            "high": counts.get("HIGH", 0),
            "medium": counts.get("MEDIUM", 0),
            "low": counts.get("LOW", 0),
        })

    return {
        "project_key": project.project_key,
        "name": project.name,
        "repository_url": project.repository_url,
        "created_at": project.created_at,
        "latest_scan": latest,
        "total_scans": len(scans),
        "latest_security_score": latest.security_score if latest and latest.security_score is not None else None,
        "latest_decision": latest.deployment_decision if latest else "PENDING",
        "sonar_quality_gate": latest.sonar_quality_gate if latest else "UNKNOWN",
        "severity_counts": {
            "CRITICAL": severity_counts.get("CRITICAL", 0),
            "HIGH": severity_counts.get("HIGH", 0),
            "MEDIUM": severity_counts.get("MEDIUM", 0),
            "LOW": severity_counts.get("LOW", 0),
        },
        "decision_counts": {
            "APPROVED": sum(1 for scan in scans if scan.deployment_decision == "APPROVED"),
            "REJECTED": sum(1 for scan in scans if scan.deployment_decision == "REJECTED"),
            "PENDING": sum(1 for scan in scans if scan.deployment_decision == "PENDING"),
        },
        "tool_health": tool_health,
        "recent_scans": scans[:10],
    }


def load_project(db: Session, project_key: str) -> Project | None:
    return db.execute(
        select(Project)
        .where(Project.project_key == project_key)
        .options(
            selectinload(Project.scans).selectinload(Scan.findings),
            selectinload(Project.scans).selectinload(Scan.tool_reports),
        )
    ).scalar_one_or_none()
