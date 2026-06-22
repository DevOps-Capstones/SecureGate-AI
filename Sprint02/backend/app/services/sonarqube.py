SEVERITY_MAP = {
    "BLOCKER": "CRITICAL",
    "CRITICAL": "CRITICAL",
    "MAJOR": "HIGH",
    "MINOR": "MEDIUM",
    "INFO": "LOW",
}


def normalize_sonarqube_report(payload: dict) -> list[dict]:
    issues = payload.get("issues", payload.get("Issues", []))
    normalized = []
    for issue in issues or []:
        raw_severity = str(issue.get("severity", "UNKNOWN")).upper()
        normalized.append(
            {
                "tool": "sonarqube",
                "severity": SEVERITY_MAP.get(raw_severity, raw_severity),
                "title": issue.get("rule") or issue.get("type") or "SonarQube issue",
                "description": issue.get("message") or issue.get("description"),
                "file": issue.get("component") or issue.get("file"),
                "source_tool": "SonarQube",
                "raw_data": issue,
            }
        )
    return normalized
