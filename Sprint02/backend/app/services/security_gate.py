def get_finding_counts(findings: list[dict]) -> dict[str, int]:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for finding in findings:
        severity = str(finding.get("severity", "UNKNOWN")).upper()
        counts[severity] = counts.get(severity, 0) + 1
    return counts
