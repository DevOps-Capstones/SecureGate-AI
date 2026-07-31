SEVERITY_MAP = {
    "BLOCKER": "CRITICAL",
    "CRITICAL": "CRITICAL",
    "MAJOR": "HIGH",
    "MINOR": "MEDIUM",
    "INFO": "LOW",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
}

QUALITY_GATE_STATUS_MAP = {
    "OK": "OK",
    "PASSED": "OK",
    "PASS": "OK",
    "SUCCESS": "OK",
    "ERROR": "ERROR",
    "FAILED": "ERROR",
    "FAIL": "ERROR",
    "WARN": "WARN",
    "WARNING": "WARN",
    "NONE": "UNKNOWN",
    "UNKNOWN": "UNKNOWN",
}


def normalize_sonarqube_report(payload: dict) -> list[dict]:
    issues = payload.get("issues") or payload.get("Issues") or payload.get("sonarqube", {}).get("issues") or []
    normalized = []
    for issue in issues or []:
        raw_severity = str(issue.get("severity") or issue.get("impactSeverity") or "UNKNOWN").upper()
        clean_code_attribute = issue.get("cleanCodeAttribute")
        issue_type = issue.get("type") or issue.get("issueType")
        normalized.append(
            {
                "tool": "sonarqube",
                "severity": SEVERITY_MAP.get(raw_severity, raw_severity),
                "title": issue.get("rule") or issue_type or clean_code_attribute or "SonarQube issue",
                "description": issue.get("message") or issue.get("description"),
                "file": issue.get("component") or issue.get("file") or issue.get("project"),
                "source_tool": "SonarQube",
                "raw_data": issue,
            }
        )
    return normalized


def _nested_get(payload: dict, *keys: str):
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def extract_quality_gate_status(payload: dict) -> str:
    candidates = [
        _nested_get(payload, "projectStatus", "status"),
        _nested_get(payload, "qualityGate", "status"),
        _nested_get(payload, "quality_gate", "status"),
        _nested_get(payload, "sonarqube", "projectStatus", "status"),
        _nested_get(payload, "sonarqube", "qualityGate", "status"),
        payload.get("qualityGateStatus"),
        payload.get("status"),
    ]
    raw_status = next((value for value in candidates if value), "UNKNOWN")
    status = str(raw_status).strip().upper()
    return QUALITY_GATE_STATUS_MAP.get(status, status)
