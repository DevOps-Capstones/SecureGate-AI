from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scan import Finding, Report, Scan
from app.services.recommendations import generate_recommendations
from app.services.repository import safe_repository_url


EXPECTED_TOOLS = ["gitleaks", "semgrep", "trivy-fs", "sonarqube", "unit-tests", "trivy-image"]


def build_master_report(scan: Scan, findings: list[Finding], evaluation: dict) -> dict:
    all_counts = Counter(item.severity.upper() for item in findings)
    tool_counts: dict[str, Counter] = defaultdict(Counter)
    for finding in findings:
        tool_counts[finding.tool][finding.severity.upper()] += 1
    uploaded_reports = {report.tool_name: report for report in scan.tool_reports}
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
    blocking_findings = [finding for finding in findings if finding.severity.upper() in {"CRITICAL", "HIGH"} or finding.tool == "gitleaks"]
    top_findings = sorted(
        blocking_findings or findings,
        key=lambda finding: (severity_order.get(finding.severity.upper(), 9), finding.tool, finding.title),
    )[:12]
    tool_summary = {}
    for tool in EXPECTED_TOOLS:
        counts = tool_counts.get(tool, Counter())
        report = uploaded_reports.get(tool)
        status = report.status if report else "NOT_UPLOADED"
        if tool == "sonarqube" and report:
            status = f"GATE_{scan.sonar_quality_gate}"
        tool_summary[tool] = {
            "status": status,
            "CRITICAL": counts.get("CRITICAL", 0),
            "HIGH": counts.get("HIGH", 0),
            "MEDIUM": counts.get("MEDIUM", 0),
            "LOW": counts.get("LOW", 0),
        }

    return {
        "executive_summary": {
            "project": scan.project_name,
            "scan_id": scan.scan_id,
            "summary": (
                f"Deployment is {evaluation['decision']} with a security score of {evaluation['score']}/100. "
                f"The assessment identified {len(findings)} normalized findings across uploaded security tools."
            ),
        },
        "security_score": {
            "score": evaluation["score"],
            "maximum": 100,
            "passing_score": evaluation["passing_score"],
            "deductions": {"critical": 20, "high": 12, "medium": 4, "low": 1},
        },
        "deployment_decision": {
            "decision": evaluation["decision"],
            "reasons": evaluation["rejected_reasons"],
        },
        "vulnerability_summary": {
            **evaluation["vulnerability_counts"],
            "secrets": evaluation["secrets_count"],
            "sonarqube_quality_gate": evaluation["sonar_quality_gate"],
        },
        "tool_findings_summary": tool_summary,
        "tool_status_summary": {tool: values["status"] for tool, values in tool_summary.items()},
        "top_findings": [
            {
                "tool": finding.tool,
                "severity": finding.severity,
                "file": finding.file,
                "title": finding.title,
                "resolution_status": finding.resolution_status,
            }
            for finding in top_findings
        ],
        "finding_counts": dict(all_counts),
        "recommendations": generate_recommendations(scan, findings),
        "report_metadata": {
            "project_name": scan.project_name,
            "repository_url": safe_repository_url(scan.repository_url),
            "image_name": scan.image_name,
            "image_tag": scan.image_tag,
            "image_full_path": scan.image_full_path,
            "branch": scan.branch,
            "commit_sha": scan.commit_sha,
            "scan_status": scan.status,
            "uploaded_at": scan.received_at.isoformat() if scan.received_at else None,
            "received_at": scan.received_at.isoformat() if scan.received_at else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_version": "1.0",
        },
    }


def persist_master_report(db: Session, scan: Scan, payload: dict) -> Report:
    report = db.execute(
        select(Report)
        .where(Report.scan_pk == scan.id, Report.report_type == "MASTER")
        .order_by(Report.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if report:
        report.payload = payload
        report.file_path = "deployment_approval.json"
        report.created_at = datetime.now(timezone.utc)
    else:
        report = Report(
            scan_pk=scan.id,
            report_type="MASTER",
            file_path="deployment_approval.json",
            payload=payload,
        )
        db.add(report)
    return report
