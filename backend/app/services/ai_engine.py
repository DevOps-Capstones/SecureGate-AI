import json
import logging
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.scan import AuditLog, Finding, Report, Scan
from app.services.master_report import build_master_report
from app.services.repository import safe_repository_url
from app.services.security_gate import evaluate_scan
from app.services.storage import save_json_report

logger = logging.getLogger(__name__)

TOOL_LABELS = {
    "gitleaks": "GitLeaks",
    "semgrep": "Semgrep",
    "trivy-fs": "Trivy Filesystem",
    "trivy-image": "Trivy Image",
    "sonarqube": "SonarQube",
    "unit-tests": "Unit Tests",
}


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = Counter((finding.severity or "UNKNOWN").upper() for finding in findings)
    return {severity: counts.get(severity, 0) for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]}


def tool_counts(findings: list[Finding]) -> dict[str, dict[str, int]]:
    output: dict[str, Counter] = defaultdict(Counter)
    for finding in findings:
        output[finding.tool][(finding.severity or "UNKNOWN").upper()] += 1
    return {tool: {severity: counts.get(severity, 0) for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]} for tool, counts in output.items()}


def top_findings(findings: list[Finding], limit: int = 8) -> list[dict[str, Any]]:
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
    sorted_findings = sorted(findings, key=lambda item: (order.get((item.severity or "UNKNOWN").upper(), 9), item.tool, item.title))
    return [
        {
            "tool": TOOL_LABELS.get(finding.tool, finding.tool),
            "severity": (finding.severity or "UNKNOWN").upper(),
            "title": finding.title,
            "file": finding.file or "Not available",
            "description": finding.description or "",
            "resolution_status": finding.resolution_status,
        }
        for finding in sorted_findings[:limit]
    ]


def _latest_report_payload(db: Session, scan: Scan) -> dict | None:
    report = db.execute(
        select(Report)
        .where(Report.scan_pk == scan.id, Report.report_type == "MASTER")
        .order_by(Report.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return report.payload if report else None


def master_context(db: Session, scan: Scan) -> dict:
    payload = _latest_report_payload(db, scan)
    if payload:
        return payload
    evaluation = evaluate_scan(scan, scan.findings)
    return build_master_report(scan, scan.findings, evaluation)


def scan_context(db: Session, scan: Scan) -> dict[str, Any]:
    findings = list(scan.findings)
    counts = severity_counts(findings)
    tools = tool_counts(findings)
    master = master_context(db, scan)
    uploaded_tools = {report.tool_name: report.status for report in scan.tool_reports}
    secrets_count = sum(1 for finding in findings if finding.tool == "gitleaks")
    code_smells = sum(1 for finding in findings if finding.tool == "sonarqube")
    blocking_findings = counts["CRITICAL"] + counts["HIGH"] + secrets_count
    readiness = "Ready for controlled deployment" if scan.deployment_decision == "APPROVED" else "Not ready for deployment"
    if scan.security_score is not None and scan.security_score < settings.security_score_threshold:
        readiness = "Not ready until score improves"

    return {
        "project_name": scan.project_name,
        "repository_url": safe_repository_url(scan.repository_url),
        "branch": scan.branch,
        "scan_id": scan.scan_id,
        "commit_sha": scan.commit_sha,
        "image_full_path": scan.image_full_path,
        "scan_status": scan.status,
        "security_score": scan.security_score,
        "deployment_decision": scan.deployment_decision,
        "sonar_quality_gate": scan.sonar_quality_gate,
        "uploaded_reports": uploaded_tools,
        "severity_counts": counts,
        "tool_counts": tools,
        "secrets_count": secrets_count,
        "code_smells": code_smells,
        "blocking_findings": blocking_findings,
        "top_findings": top_findings(findings),
        "master_report": master,
        "ai_readiness": readiness,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def deterministic_insights(context: dict[str, Any]) -> dict[str, Any]:
    counts = context["severity_counts"]
    score = context.get("security_score")
    decision = context.get("deployment_decision")
    top = context.get("top_findings", [])
    blockers = []
    if context.get("secrets_count", 0) > 0:
        blockers.append("Remove detected secrets, rotate exposed credentials, and move values to CI/CD secrets.")
    if counts.get("CRITICAL", 0) > 0:
        blockers.append("Fix critical vulnerabilities before any production deployment.")
    if counts.get("HIGH", 0) > settings.high_vulnerability_threshold:
        blockers.append("Reduce high-severity vulnerabilities below the configured production threshold.")
    if context.get("sonar_quality_gate") not in {"OK", "UNKNOWN"}:
        blockers.append("Resolve SonarQube quality gate issues and rerun the pipeline.")
    if score is not None and score < settings.security_score_threshold:
        blockers.append(f"Raise the security score to at least {settings.security_score_threshold}.")

    if not blockers:
        blockers.append("No blocking issue is visible. Keep monitoring dependencies, image risk, and code quality on every branch.")

    recommendations = blockers[:]
    for finding in top[:4]:
        recommendations.append(f"{finding['severity']} from {finding['tool']}: fix {finding['title']} in {finding['file']}.")

    overall_risk = "Critical" if counts.get("CRITICAL", 0) or context.get("secrets_count", 0) else "High" if counts.get("HIGH", 0) else "Medium" if counts.get("MEDIUM", 0) else "Low"
    fix_hours = 1 + counts.get("CRITICAL", 0) * 6 + counts.get("HIGH", 0) * 3 + counts.get("MEDIUM", 0)
    return {
        "executive_summary": (
            f"{context['project_name']} is {decision}. The latest scan scored {score if score is not None else 'pending'}/100 "
            f"with {counts.get('CRITICAL', 0)} critical, {counts.get('HIGH', 0)} high, "
            f"{counts.get('MEDIUM', 0)} medium, and {counts.get('LOW', 0)} low findings."
        ),
        "overall_risk": overall_risk,
        "ai_readiness": context["ai_readiness"],
        "deployment_recommendation": "Proceed only after policy approval." if decision == "APPROVED" else "Do not deploy until blockers are fixed and the pipeline is rescanned.",
        "estimated_fix_time": f"About {fix_hours} engineering hour{'s' if fix_hours != 1 else ''}, depending on package ownership and test coverage.",
        "top_recommendations": recommendations[:8],
        "confidence": "Medium",
    }


def _finding_priority(finding: Finding) -> tuple[int, str]:
    severity = (finding.severity or "UNKNOWN").upper()
    tool = finding.tool
    title = finding.title.lower()
    if tool == "gitleaks":
        return 2, "Hardcoded Secrets"
    if tool == "unit-tests":
        return 7, "Technical Debt"
    if tool == "sonarqube" and ("quality gate" in title or severity in {"CRITICAL", "HIGH"}):
        return 3, "Quality Gate Failures"
    if severity == "CRITICAL":
        return 4, "Critical CVEs"
    if severity == "HIGH":
        return 5, "High Vulnerabilities"
    if tool == "sonarqube":
        return 6, "Code Smells"
    return 7, "Technical Debt"


def _estimated_minutes(finding: Finding) -> int:
    severity = (finding.severity or "UNKNOWN").upper()
    if finding.tool == "gitleaks":
        return 15
    if severity == "CRITICAL":
        return 90
    if severity == "HIGH":
        return 60
    if severity == "MEDIUM":
        return 30
    return 15


def _assigned_area_from_tool(tool: str) -> str:
    if tool in {"gitleaks", "trivy-image"}:
        return "DevOps"
    if tool in {"semgrep", "sonarqube", "unit-tests"}:
        return "Backend"
    if tool == "trivy-fs":
        return "Dependencies"
    return "Application"


def _recommended_version(finding: Finding) -> str:
    raw = finding.raw_data or {}
    return str(raw.get("FixedVersion") or raw.get("fixed_version") or raw.get("fixedVersion") or "Use the fixed version recommended by the scanner.")


def _root_cause(finding: Finding) -> str:
    if finding.tool == "gitleaks":
        return "A secret-like value was committed into source-controlled files."
    if finding.tool.startswith("trivy"):
        return "A dependency, operating-system package, or image layer has a known vulnerability."
    if finding.tool == "semgrep":
        return "Static analysis detected an insecure coding pattern in the application source."
    if finding.tool == "sonarqube":
        return "Code quality or maintainability analysis found an issue that affects the quality gate."
    if finding.tool == "unit-tests":
        return "The test stage reported missing, skipped, or failed validation."
    return "SecureGate normalized this issue from an uploaded tool report."


def _business_impact(finding: Finding) -> str:
    severity = (finding.severity or "UNKNOWN").upper()
    if finding.tool == "gitleaks":
        return "Exposed credentials can allow unauthorized access and must be rotated before deployment."
    if severity == "CRITICAL":
        return "Critical vulnerabilities can create immediate production compromise risk."
    if severity == "HIGH":
        return "High vulnerabilities can significantly increase exploitability or compliance risk."
    if severity == "MEDIUM":
        return "Medium findings should be fixed in the next remediation cycle to keep the project healthy."
    return "Track and resolve this issue to reduce long-term operational risk."


def _fix_steps(finding: Finding) -> list[str]:
    if finding.tool == "gitleaks":
        return ["Remove the secret from the affected file.", "Rotate the exposed credential in the provider console.", "Store the new value in GitHub Actions, Jenkins, or platform secrets.", "Rerun GitLeaks and SecureGate AI to confirm the secret is no longer detected."]
    if finding.tool.startswith("trivy"):
        return ["Identify the vulnerable package or image layer from the tool report.", "Upgrade the dependency, package, or base image to a fixed version.", "Rebuild the application and Docker image.", "Rerun Trivy and SecureGate AI to verify the finding is cleared."]
    if finding.tool in {"semgrep", "sonarqube"}:
        return ["Open the affected file and review the scanner message.", "Refactor the unsafe pattern or code quality issue.", "Run unit tests and static analysis locally when possible.", "Push the fix and rerun the SecureGate AI pipeline."]
    if finding.tool == "unit-tests":
        return ["Add or fix the failing test configuration.", "Run the test command locally.", "Commit the test fix and rerun the CI/CD pipeline."]
    return ["Review the source tool report, fix the affected file, and rerun the SecureGate AI pipeline."]


def _example_configuration(finding: Finding) -> str:
    if finding.tool == "gitleaks":
        return "Before: API_TOKEN=plain-text-value | After: API_TOKEN=${API_TOKEN}"
    if finding.tool.startswith("trivy"):
        return "Before: use an unfixed dependency/base image | After: pin or upgrade to the scanner-recommended fixed version."
    if finding.tool in {"semgrep", "sonarqube"}:
        return "Before: unsafe or hardcoded pattern | After: use validated inputs, environment variables, or a simpler maintainable function."
    if finding.tool == "unit-tests":
        return "Before: no supported test command | After: add a repeatable npm test, pytest, or equivalent CI command."
    return "Use the remediation guidance from the source tool report."


def _remediation_detail(finding: Finding) -> dict[str, Any]:
    priority, category = _finding_priority(finding)
    minutes = _estimated_minutes(finding)
    return {
        "issue_name": finding.title,
        "tool": TOOL_LABELS.get(finding.tool, finding.tool),
        "source_tool": finding.tool,
        "severity": (finding.severity or "UNKNOWN").upper(),
        "location": finding.file or "Not available",
        "affected_file": finding.file or "Not available",
        "root_cause": _root_cause(finding),
        "business_impact": _business_impact(finding),
        "why_it_matters": finding.description or _business_impact(finding),
        "step_by_step_fix": _fix_steps(finding),
        "verification_steps": ["Commit the remediation change.", "Rerun the same CI/CD pipeline.", "Confirm the related tool report no longer contains this finding.", "Confirm SecureGate AI deployment decision and score improve."],
        "recommended_version": _recommended_version(finding),
        "example_configuration": _example_configuration(finding),
        "estimated_time": f"{minutes} min",
        "estimated_minutes": minutes,
        "priority": priority,
        "priority_label": category,
        "status": finding.resolution_status,
    }


def _format_minutes(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _remediation_prompt(payload: dict[str, Any]) -> str:
    compact = {
        "project": payload["project_name"],
        "decision": payload["deployment_decision"],
        "score": payload["security_score"],
        "risk": payload["overall_risk"],
        "counts": payload["finding_counts"],
        "top_risks": payload["top_three_risks"],
        "actions": [item["issue_name"] for item in payload["detailed_remediation"][:5]],
    }
    return "You are SecureGate AI. Give one short final remediation recommendation using only this context. Do not invent vulnerabilities, file names, CVEs, or secrets.\n\nContext:\n" + json.dumps(compact, indent=2)


def remediation_context_text(payload: dict[str, Any]) -> str:
    actions = payload.get("detailed_remediation", [])[:6]
    action_text = "; ".join(f"P{item.get('priority')} {item.get('severity')} {item.get('tool')} {item.get('issue_name')} in {item.get('affected_file')}" for item in actions) or "No remediation actions required."
    blockers = "; ".join(payload.get("remaining_blockers", [])) or "No blockers listed."
    counts = payload.get("finding_counts", {})
    return (
        f"Project {payload.get('project_name')}. Decision {payload.get('deployment_decision')}. "
        f"Score {payload.get('security_score')}/100. Risk {payload.get('overall_risk')}. "
        f"Counts C{counts.get('CRITICAL', 0)} H{counts.get('HIGH', 0)} M{counts.get('MEDIUM', 0)} L{counts.get('LOW', 0)} Secrets {counts.get('secrets', 0)}. "
        f"Overall priority {payload.get('overall_priority')}. Estimated fix time {payload.get('estimated_fix_time')}. "
        f"Blockers: {blockers}. Actions: {action_text}. Final recommendation: {payload.get('final_recommendation')}"
    )


def call_ollama(prompt: str) -> tuple[str | None, str]:
    if not settings.ai_enabled:
        return None, "DISABLED"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.2, "num_predict": 90, "num_ctx": 1024},
    }
    request = urllib.request.Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.ollama_timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
            return str(data.get("response", "")).strip(), "AVAILABLE"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Ollama request failed: %s", exc)
        return None, "UNAVAILABLE"


def _compact_findings(context: dict[str, Any], limit: int = 5) -> str:
    findings = context.get("top_findings", [])[:limit]
    if not findings:
        return "No top findings stored."
    return "; ".join(
        f"{item.get('severity')} {item.get('tool')} in {item.get('file')}: {item.get('title')}"
        for item in findings
    )[:1400]


def _compact_context_text(context: dict[str, Any]) -> str:
    counts = context.get("severity_counts", {})
    tools = context.get("tool_counts", {})
    return (
        f"Project: {context.get('project_name')}\n"
        f"Repository: {context.get('repository_url')}\n"
        f"Branch: {context.get('branch')}\n"
        f"Scan ID: {context.get('scan_id')}\n"
        f"Decision: {context.get('deployment_decision')}\n"
        f"Score: {context.get('security_score')}/100\n"
        f"Sonar gate: {context.get('sonar_quality_gate')}\n"
        f"Counts: critical {counts.get('CRITICAL', 0)}, high {counts.get('HIGH', 0)}, medium {counts.get('MEDIUM', 0)}, low {counts.get('LOW', 0)}, unknown {counts.get('UNKNOWN', 0)}\n"
        f"Secrets: {context.get('secrets_count', 0)}\n"
        f"Code smells: {context.get('code_smells', 0)}\n"
        f"Tool counts: {json.dumps(tools)}\n"
        f"Readiness: {context.get('ai_readiness')}\n"
        f"Top findings: {_compact_findings(context)}"
    )


def insight_prompt(context: dict[str, Any]) -> str:
    return (
        "You are SecureGate AI, a concise DevSecOps assistant. Explain the scan in simple words. "
        "Use only the provided context. Return short sections: Executive summary, Deployment readiness, Main fixes, Estimated effort.\n\n"
        f"Context:\n{_compact_context_text(context)}"
    )


def _chat_context_text(context: dict[str, Any]) -> str:
    counts = context.get("severity_counts", {})
    blockers = []
    if counts.get("CRITICAL", 0):
        blockers.append(f"{counts.get('CRITICAL')} critical vulnerabilities")
    if counts.get("HIGH", 0):
        blockers.append(f"{counts.get('HIGH')} high vulnerabilities")
    if context.get("secrets_count", 0):
        blockers.append(f"{context.get('secrets_count')} secrets")
    if context.get("sonar_quality_gate") not in {"OK", "UNKNOWN"}:
        blockers.append(f"Sonar quality gate {context.get('sonar_quality_gate')}")
    score = context.get("security_score")
    if score is not None and score < settings.security_score_threshold:
        blockers.append(f"score below {settings.security_score_threshold}")
    return (
        f"Project {context.get('project_name')}. "
        f"Decision {context.get('deployment_decision')}. "
        f"Score {context.get('security_score')}/100. "
        f"Counts C{counts.get('CRITICAL', 0)} H{counts.get('HIGH', 0)} M{counts.get('MEDIUM', 0)} L{counts.get('LOW', 0)}. "
        f"Sonar {context.get('sonar_quality_gate')}. "
        f"Branch {context.get('branch')}. "
        f"Main blockers: {', '.join(blockers) if blockers else 'none visible'}. "
        f"Top findings: {_compact_findings(context, 3)}. "
        f"Remediation plan: {context.get('remediation_context', 'No remediation plan generated yet.')}"
    )


def chat_prompt(context: dict[str, Any], question: str) -> str:
    return (
        "You are SecureGate AI Chat Assistant. Answer in 1 to 3 short sentences using only this scan context. "
        "Be direct and practical.\n\n"
        f"Scan context: {_chat_context_text(context)}\n"
        f"Question: {question}"
    )


def build_ai_insights(db: Session, scan: Scan) -> dict[str, Any]:
    context = scan_context(db, scan)
    fallback = deterministic_insights(context)
    db.add(AuditLog(scan_pk=scan.id, action="AI_REQUEST", message="AI insight generation requested.", actor="system", log_metadata={"model": settings.ollama_model}))
    ai_text, ollama_status = call_ollama(insight_prompt(context))
    payload = {
        **fallback,
        "scan_id": scan.scan_id,
        "project_name": scan.project_name,
        "repository_url": context["repository_url"],
        "branch": scan.branch,
        "model": settings.ollama_model,
        "ollama_status": ollama_status,
        "ai_text": ai_text or "Ollama is unavailable, so SecureGate AI is showing deterministic rule-based guidance until the local model responds.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    file_path = save_json_report(scan.scan_id, "AI_SUMMARY", payload)
    report = db.execute(
        select(Report)
        .where(Report.scan_pk == scan.id, Report.report_type == "AI_SUMMARY")
        .order_by(Report.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if report:
        report.payload = payload
        report.file_path = file_path
        report.created_at = datetime.now(timezone.utc)
    else:
        db.add(Report(scan_pk=scan.id, report_type="AI_SUMMARY", file_path=file_path, payload=payload))
    db.add(AuditLog(scan_pk=scan.id, action="AI_RESPONSE", message=f"AI insight response status: {ollama_status}.", actor="system", log_metadata={"model": settings.ollama_model, "ollama_status": ollama_status}))
    db.commit()
    return payload


def build_remediation_payload(db: Session, scan: Scan, refresh: bool = False) -> dict[str, Any]:
    existing = db.execute(
        select(Report)
        .where(Report.scan_pk == scan.id, Report.report_type == "AI_REMEDIATION")
        .order_by(Report.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if existing and not refresh:
        return existing.payload

    context = scan_context(db, scan)
    insights = deterministic_insights(context)
    master = context["master_report"]
    findings = sorted(list(scan.findings), key=lambda item: (_finding_priority(item)[0], item.severity, item.tool, item.title))
    important_findings = findings[:24]
    details = [_remediation_detail(finding) for finding in important_findings]
    total_minutes = sum(item["estimated_minutes"] for item in details) or 15
    counts = context["severity_counts"]
    secrets_count = context["secrets_count"]
    total_findings = sum(counts.values())
    checklist = [
        {"label": "Remove exposed secrets", "complete": secrets_count == 0},
        {"label": "Fix critical vulnerabilities", "complete": counts.get("CRITICAL", 0) == 0},
        {"label": "Reduce high vulnerabilities", "complete": counts.get("HIGH", 0) <= settings.high_vulnerability_threshold},
        {"label": "Pass SonarQube Quality Gate", "complete": scan.sonar_quality_gate in {"OK", "UNKNOWN"}},
        {"label": "Rebuild Docker Image", "complete": bool(scan.image_full_path)},
        {"label": "Re-run SecureGate AI Scan", "complete": scan.status == "COMPLETED"},
    ]
    completed = sum(1 for item in checklist if item["complete"])
    completion_percentage = round((completed / len(checklist)) * 100) if checklist else 0
    timeline = [
        {
            "task": item["issue_name"],
            "estimated_time": item["estimated_time"],
            "priority": item["priority"],
            "assigned_area": _assigned_area_from_tool(item["source_tool"]),
        }
        for item in details[:12]
    ]
    if not timeline:
        timeline = [{"task": "Continue monitoring clean scans", "estimated_time": "15 min", "priority": 7, "assigned_area": "DevOps"}]
    top_three = [
        {"issue": item["issue_name"], "severity": item["severity"], "tool": item["tool"], "location": item["location"]}
        for item in details[:3]
    ]
    production_ready = scan.deployment_decision == "APPROVED" and counts.get("CRITICAL", 0) == 0 and secrets_count == 0 and scan.sonar_quality_gate in {"OK", "UNKNOWN"}
    blockers = []
    if scan.deployment_decision != "APPROVED":
        blockers.extend(master.get("deployment_decision", {}).get("reasons", []) or ["Deployment decision is not approved."])
    if counts.get("CRITICAL", 0):
        blockers.append("Critical vulnerabilities remain unresolved.")
    if secrets_count:
        blockers.append("Secrets remain in source-controlled files.")
    if scan.sonar_quality_gate not in {"OK", "UNKNOWN"}:
        blockers.append(f"SonarQube quality gate is {scan.sonar_quality_gate}.")
    payload = {
        "scan_id": scan.scan_id,
        "project_name": scan.project_name,
        "repository_url": context["repository_url"],
        "branch": scan.branch,
        "commit_sha": scan.commit_sha,
        "deployment_decision": scan.deployment_decision,
        "security_score": scan.security_score,
        "ai_readiness_score": max(0, min(100, completion_percentage if production_ready else min(completion_percentage, scan.security_score or 0))),
        "overall_priority": details[0]["priority_label"] if details else "Monitoring",
        "overall_risk": insights["overall_risk"],
        "estimated_fix_time": _format_minutes(total_minutes),
        "total_findings": total_findings,
        "total_recommended_actions": len(details),
        "finding_counts": {"CRITICAL": counts.get("CRITICAL", 0), "HIGH": counts.get("HIGH", 0), "MEDIUM": counts.get("MEDIUM", 0), "LOW": counts.get("LOW", 0), "UNKNOWN": counts.get("UNKNOWN", 0), "secrets": secrets_count, "quality_gate": scan.sonar_quality_gate},
        "top_three_risks": top_three,
        "priority_matrix": [{"issue": item["issue_name"], "severity": item["severity"], "tool": item["tool"], "estimated_fix_time": item["estimated_time"], "status": item["status"], "priority": item["priority"], "priority_label": item["priority_label"]} for item in details],
        "detailed_remediation": details,
        "remediation_steps": [{"priority": item["priority"], "action": item["issue_name"], "owner": _assigned_area_from_tool(item["source_tool"]), "validation": "Commit fix, rerun SecureGate pipeline, and confirm deployment decision becomes APPROVED."} for item in details],
        "production_readiness_checklist": checklist,
        "completion_percentage": completion_percentage,
        "remediation_timeline": timeline,
        "production_ready": production_ready,
        "remaining_blockers": blockers,
        "final_recommendation": "Production ready. Continue normal monitoring and rerun SecureGate AI on every branch push." if production_ready else "Not production ready. Complete the highest-priority remediation items and rerun SecureGate AI before deployment.",
        "ai_recommendation": insights["deployment_recommendation"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.ollama_model,
        "ollama_status": "NOT_REQUESTED",
    }
    if refresh:
        ai_text, ollama_status = call_ollama(_remediation_prompt(payload))
        payload["ollama_status"] = ollama_status
        if ai_text:
            payload["final_recommendation"] = ai_text
    file_path = save_json_report(scan.scan_id, "AI_REMEDIATION", payload)
    if existing:
        existing.payload = payload
        existing.file_path = file_path
        existing.created_at = datetime.now(timezone.utc)
    else:
        db.add(Report(scan_pk=scan.id, report_type="AI_REMEDIATION", file_path=file_path, payload=payload))
    db.commit()
    return payload
