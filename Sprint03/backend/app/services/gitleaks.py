def normalize_gitleaks_report(payload: dict | list) -> list[dict]:
    findings = payload if isinstance(payload, list) else payload.get("findings", payload.get("Findings", []))
    normalized = []
    for item in findings or []:
        normalized.append(
            {
                "tool": "gitleaks",
                "severity": "HIGH",
                "title": item.get("RuleID") or item.get("rule") or "Secret detected",
                "description": item.get("Description") or item.get("description") or "GitLeaks detected a potential secret.",
                "file": item.get("File") or item.get("file"),
                "source_tool": "GitLeaks",
                "raw_data": item,
            }
        )
    return normalized
