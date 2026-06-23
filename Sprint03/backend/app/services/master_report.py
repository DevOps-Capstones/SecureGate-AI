from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scan import Finding, Report, Scan
from app.services.recommendations import generate_recommendations


def build_master_report(scan: Scan, findings: list[Finding], evaluation: dict) -> dict:
    all_counts = Counter(item.severity.upper() for item in findings)
    tool_counts: dict[str, Counter] = defaultdict(Counter)
    for finding in findings:
        tool_counts[finding.tool][finding.severity.upper()] += 1

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
            "deductions": {"critical": 15, "high": 8, "medium": 3},
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
        "tool_findings_summary": {
            tool: dict(counts) for tool, counts in sorted(tool_counts.items())
        },
        "finding_counts": dict(all_counts),
        "recommendations": generate_recommendations(scan, findings),
        "report_metadata": {
            "project_name": scan.project_name,
            "repository_url": scan.repository_url,
            "branch": scan.branch,
            "commit_sha": scan.commit_sha,
            "scan_status": scan.status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_version": "1.0",
        },
    }


def persist_master_report(db: Session, scan: Scan, payload: dict) -> Report:
    report = db.execute(
        select(Report).where(Report.scan_pk == scan.id, Report.report_type == "MASTER")
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
