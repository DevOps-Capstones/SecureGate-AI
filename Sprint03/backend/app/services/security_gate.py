from collections import Counter
from datetime import datetime, timezone

from app.models.scan import Finding, Scan

PASSING_SCORE = 80
DEDUCTIONS = {"CRITICAL": 15, "HIGH": 8, "MEDIUM": 3}


def calculate_security_score(findings: list[Finding]) -> tuple[int, dict[str, int]]:
    vulnerabilities = [finding for finding in findings if finding.tool in {"trivy-fs", "trivy-image"}]
    counts = Counter(finding.severity.upper() for finding in vulnerabilities)
    deduction = sum(counts[severity] * points for severity, points in DEDUCTIONS.items())
    return max(0, 100 - deduction), {severity: counts.get(severity, 0) for severity in DEDUCTIONS}


def evaluate_scan(scan: Scan, findings: list[Finding]) -> dict:
    score, vulnerability_counts = calculate_security_score(findings)
    secrets_count = sum(1 for finding in findings if finding.tool == "gitleaks")
    quality_gate_failed = scan.sonar_quality_gate in {"ERROR", "FAILED", "FAIL"}
    rejected_reasons = []
    if secrets_count:
        rejected_reasons.append("Secrets were detected.")
    if vulnerability_counts["CRITICAL"]:
        rejected_reasons.append("Critical vulnerabilities were detected.")
    if quality_gate_failed:
        rejected_reasons.append("The SonarQube quality gate failed.")
    if score < PASSING_SCORE:
        rejected_reasons.append(f"Security score {score} is below the passing score of {PASSING_SCORE}.")

    decision = "REJECTED" if rejected_reasons else "APPROVED"
    scan.security_score = score
    scan.deployment_decision = decision
    scan.evaluated_at = datetime.now(timezone.utc)
    return {
        "score": score,
        "decision": decision,
        "passing_score": PASSING_SCORE,
        "secrets_count": secrets_count,
        "vulnerability_counts": vulnerability_counts,
        "sonar_quality_gate": scan.sonar_quality_gate,
        "rejected_reasons": rejected_reasons,
    }
