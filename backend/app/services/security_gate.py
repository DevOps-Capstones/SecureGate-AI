from collections import Counter
from datetime import datetime, timezone

from app.config.settings import settings
from app.models.scan import Finding, Scan

DEDUCTIONS = {"CRITICAL": 20, "HIGH": 12, "MEDIUM": 4, "LOW": 1}


def calculate_security_score(findings: list[Finding]) -> tuple[int, dict[str, int]]:
    vulnerabilities = [finding for finding in findings if finding.tool in {"trivy-fs", "trivy-image", "semgrep", "sonarqube", "unit-tests"}]
    counts = Counter(finding.severity.upper() for finding in vulnerabilities)
    deduction = sum(counts[severity] * points for severity, points in DEDUCTIONS.items())
    return max(0, 100 - deduction), {severity: counts.get(severity, 0) for severity in DEDUCTIONS}


def evaluate_scan(scan: Scan, findings: list[Finding]) -> dict:
    score, vulnerability_counts = calculate_security_score(findings)
    secrets_count = sum(1 for finding in findings if finding.tool == "gitleaks")
    quality_gate_failed = bool(scan.sonar_quality_gate) and scan.sonar_quality_gate not in {"OK", "UNKNOWN"}
    unit_tests_failed = any(finding.tool == "unit-tests" for finding in findings)
    rejected_reasons = []
    if settings.secret_detection_required and secrets_count:
        rejected_reasons.append("Secrets were detected.")
    if vulnerability_counts["CRITICAL"]:
        rejected_reasons.append("Critical vulnerabilities were detected. Production deployment is blocked until fixed.")
    if settings.block_high_vulnerabilities and vulnerability_counts["HIGH"] > settings.high_vulnerability_threshold:
        rejected_reasons.append(f"High vulnerabilities exceeded the allowed threshold of {settings.high_vulnerability_threshold}.")
    if settings.quality_gate_required and quality_gate_failed:
        rejected_reasons.append("The SonarQube quality gate failed.")
    if unit_tests_failed:
        rejected_reasons.append("Unit tests failed.")
    if score < settings.security_score_threshold:
        rejected_reasons.append(f"Security score {score} is below the production passing score of {settings.security_score_threshold}.")

    decision = "REJECTED" if rejected_reasons else "APPROVED"
    scan.security_score = score
    scan.deployment_decision = decision
    scan.evaluated_at = datetime.now(timezone.utc)
    return {
        "score": score,
        "decision": decision,
        "passing_score": settings.security_score_threshold,
        "secrets_count": secrets_count,
        "vulnerability_counts": vulnerability_counts,
        "sonar_quality_gate": scan.sonar_quality_gate,
        "rejected_reasons": rejected_reasons,
    }
