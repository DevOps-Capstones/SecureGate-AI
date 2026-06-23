from app.models.scan import Finding, Scan


def generate_recommendations(scan: Scan, findings: list[Finding]) -> list[dict]:
    recommendations: list[dict] = []
    critical = [item for item in findings if item.tool.startswith("trivy") and item.severity == "CRITICAL"]
    high = [item for item in findings if item.tool.startswith("trivy") and item.severity == "HIGH"]
    medium = [item for item in findings if item.tool.startswith("trivy") and item.severity == "MEDIUM"]
    secrets = [item for item in findings if item.tool == "gitleaks"]

    if secrets:
        recommendations.append({
            "priority": 1,
            "category": "Secrets",
            "title": "Remove and rotate exposed credentials",
            "actions": ["Remove secrets from source control.", "Move values to GitHub Secrets.", "Rotate every exposed credential."],
        })
    if critical:
        recommendations.append({
            "priority": 1,
            "category": "Critical vulnerabilities",
            "title": "Remediate critical CVEs before deployment",
            "actions": ["Upgrade vulnerable packages.", "Use a supported latest base image.", "Patch or replace affected dependencies."],
        })
    if scan.sonar_quality_gate in {"ERROR", "FAILED", "FAIL"}:
        recommendations.append({
            "priority": 1,
            "category": "Code quality",
            "title": "Restore the SonarQube quality gate",
            "actions": ["Resolve blocking code smells.", "Increase test coverage.", "Fix maintainability and reliability issues."],
        })
    if high:
        recommendations.append({
            "priority": 2,
            "category": "High vulnerabilities",
            "title": "Schedule high-severity dependency updates",
            "actions": ["Apply fixed package versions.", "Rebuild and rescan the image.", "Track unavailable fixes with an owner and due date."],
        })
    if medium:
        recommendations.append({
            "priority": 3,
            "category": "Medium vulnerabilities",
            "title": "Reduce the remaining vulnerability backlog",
            "actions": ["Prioritize internet-facing components.", "Update transitive dependencies.", "Verify fixes in the next CI scan."],
        })
    if not recommendations:
        recommendations.append({
            "priority": 3,
            "category": "Security hygiene",
            "title": "Maintain the current security posture",
            "actions": ["Keep dependencies current.", "Continue scanning every commit.", "Review new CVE disclosures regularly."],
        })
    return sorted(recommendations, key=lambda item: (item["priority"], item["category"]))
