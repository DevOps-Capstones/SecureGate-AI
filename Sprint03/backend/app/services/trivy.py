def normalize_trivy_report(payload: dict, tool: str) -> list[dict]:
    normalized = []
    for result in payload.get("Results", []) or []:
        target = result.get("Target")
        for vulnerability in result.get("Vulnerabilities", []) or []:
            normalized.append(
                {
                    "tool": tool,
                    "severity": vulnerability.get("Severity", "UNKNOWN").upper(),
                    "title": vulnerability.get("Title") or vulnerability.get("VulnerabilityID") or "Vulnerability detected",
                    "description": vulnerability.get("Description"),
                    "file": target,
                    "source_tool": "Trivy",
                    "raw_data": vulnerability,
                }
            )
    return normalized
