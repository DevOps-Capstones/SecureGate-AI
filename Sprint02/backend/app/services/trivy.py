import json
import subprocess
from pathlib import Path

from app.config.settings import settings
from app.services.gitleaks import ScannerExecutionError

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def run_trivy_fs_scan(repository_path: Path) -> dict:
    command = [
        "trivy",
        "fs",
        "--format",
        "json",
        "--scanners",
        "vuln",
        "--quiet",
        "--exit-code",
        "0",
        str(repository_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.scan_timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ScannerExecutionError("Trivy executable was not found in the backend runtime.") from exc

    if result.returncode != 0:
        raise ScannerExecutionError(result.stderr.strip() or result.stdout.strip() or "Trivy filesystem scan failed.")

    payload = json.loads(result.stdout or "{}")
    counts = {severity.lower(): 0 for severity in SEVERITIES}
    findings = []

    for result_item in payload.get("Results", []):
        target = result_item.get("Target")
        for vulnerability in result_item.get("Vulnerabilities", []) or []:
            severity = vulnerability.get("Severity", "UNKNOWN").upper()
            if severity in SEVERITIES:
                counts[severity.lower()] += 1
            findings.append(
                {
                    "scanner_type": "trivy",
                    "severity": severity,
                    "file_path": target,
                    "line_number": None,
                    "title": vulnerability.get("Title") or vulnerability.get("VulnerabilityID"),
                    "description": vulnerability.get("Description"),
                    "vulnerability_id": vulnerability.get("VulnerabilityID"),
                    "raw_data": vulnerability,
                }
            )

    return {
        "critical_count": counts["critical"],
        "high_count": counts["high"],
        "medium_count": counts["medium"],
        "low_count": counts["low"],
        "findings": findings,
    }
