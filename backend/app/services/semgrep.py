SEVERITY_MAP = {
    "ERROR": "HIGH",
    "WARNING": "MEDIUM",
    "INFO": "LOW",
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
}


def normalize_semgrep_report(payload: dict) -> list[dict]:
    normalized = []
    for result in payload.get("results", []) or []:
        extra = result.get("extra", {}) or {}
        metadata = extra.get("metadata", {}) or {}
        raw_severity = str(extra.get("severity") or metadata.get("impact") or "LOW").upper()
        normalized.append({
            "tool": "semgrep",
            "severity": SEVERITY_MAP.get(raw_severity, raw_severity),
            "title": extra.get("message") or result.get("check_id") or "Semgrep finding",
            "description": extra.get("message") or metadata.get("description"),
            "file": result.get("path"),
            "source_tool": "Semgrep",
            "raw_data": result,
        })
    return normalized
