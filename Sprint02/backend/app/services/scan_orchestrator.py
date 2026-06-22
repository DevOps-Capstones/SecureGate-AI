from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.scan import AuditLog, Finding, Project, Scan, ToolReport
from app.services.gitleaks import normalize_gitleaks_report
from app.services.repository import normalize_repository_url
from app.services.scan_id import generate_scan_id
from app.services.sonarqube import normalize_sonarqube_report
from app.services.trivy import normalize_trivy_report

REQUIRED_TOOLS = {"gitleaks", "trivy-fs", "trivy-image", "sonarqube"}

TOOL_NORMALIZERS = {
    "gitleaks": normalize_gitleaks_report,
    "trivy-fs": lambda payload: normalize_trivy_report(payload, "trivy-fs"),
    "trivy-image": lambda payload: normalize_trivy_report(payload, "trivy-image"),
    "sonarqube": normalize_sonarqube_report,
}


def _audit(db: Session, scan: Scan | None, action: str, message: str, metadata: dict | None = None) -> None:
    db.add(
        AuditLog(
            scan_pk=scan.id if scan else None,
            action=action,
            message=message,
            log_metadata=metadata or {},
        )
    )


def create_scan_record(db: Session, project_name: str, repository_url: str, branch: str, commit_sha: str) -> Scan:
    normalized_url = normalize_repository_url(repository_url)
    project = db.execute(
        select(Project).where(Project.name == project_name, Project.repository_url == normalized_url)
    ).scalar_one_or_none()
    if not project:
        project = Project(name=project_name, repository_url=normalized_url)
        db.add(project)
        db.flush()

    scan = Scan(
        scan_id=generate_scan_id(db),
        project_id=project.id,
        project_name=project_name,
        repository_url=normalized_url,
        branch=branch,
        commit_sha=commit_sha,
        status="RECEIVED",
        received_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.flush()
    _audit(db, scan, "SCAN_RECEIVED", "Scan metadata received from CI pipeline.")
    db.commit()
    db.refresh(scan)
    return scan


def ingest_tool_report(db: Session, scan_id: str, tool_name: str, payload: dict | list) -> tuple[Scan, ToolReport, list[Finding]]:
    scan = db.execute(
        select(Scan).where(Scan.scan_id == scan_id).options(selectinload(Scan.tool_reports))
    ).scalar_one_or_none()
    if not scan:
        raise LookupError("Scan not found")

    normalizer = TOOL_NORMALIZERS[tool_name]
    scan.status = "PROCESSING"
    db.flush()

    try:
        normalized_findings = normalizer(payload)
        report = ToolReport(
            scan_pk=scan.id,
            tool_name=tool_name,
            status="UPLOADED",
            raw_payload=payload if isinstance(payload, dict) else {"items": payload},
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

        uploaded_tools = {item.tool_name for item in scan.tool_reports}
        uploaded_tools.add(tool_name)
        if REQUIRED_TOOLS.issubset(uploaded_tools):
            scan.status = "COMPLETED"
            scan.completed_at = datetime.now(timezone.utc)
        else:
            scan.status = "PROCESSING"
            scan.completed_at = None
        _audit(
            db,
            scan,
            "REPORT_UPLOADED",
            f"{tool_name} report uploaded and normalized.",
            {"tool": tool_name, "findings_count": len(finding_models)},
        )
        db.commit()
        db.refresh(scan)
        db.refresh(report)
        return scan, report, finding_models
    except Exception as exc:
        db.rollback()
        failed_scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalar_one()
        failed_scan.status = "FAILED"
        failed_scan.completed_at = datetime.now(timezone.utc)
        _audit(db, failed_scan, "REPORT_NORMALIZATION_FAILED", str(exc), {"tool": tool_name})
        db.commit()
        raise


def get_dashboard_summary(db: Session) -> dict:
    total_projects = db.execute(select(func.count(Project.id))).scalar_one()
    total_scans = db.execute(select(func.count(Scan.id))).scalar_one()
    recent_scans = db.execute(select(Scan).order_by(Scan.received_at.desc()).limit(10)).scalars().all()
    latest_uploads = db.execute(select(ToolReport).order_by(ToolReport.uploaded_at.desc()).limit(10)).scalars().all()
    recent_findings = db.execute(select(Finding).order_by(Finding.created_at.desc()).limit(10)).scalars().all()
    return {
        "total_projects": total_projects,
        "total_scans": total_scans,
        "recent_scans": recent_scans,
        "latest_uploads": latest_uploads,
        "most_recent_findings": recent_findings,
    }
