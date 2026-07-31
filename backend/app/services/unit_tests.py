def normalize_unit_tests_report(payload: dict) -> list[dict]:
    status = str(payload.get("status", "UNKNOWN")).upper()
    if status != "FAILED":
        return []
    return [{
        "tool": "unit-tests",
        "severity": "HIGH",
        "title": "Unit tests failed",
        "description": payload.get("reason") or "One or more unit tests failed in the CI runner.",
        "file": payload.get("framework") or "unit-tests",
        "source_tool": "Unit Tests",
        "raw_data": payload,
    }]
