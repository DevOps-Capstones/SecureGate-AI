import json
import subprocess
from pathlib import Path

from app.config.settings import settings


class ScannerExecutionError(RuntimeError):
    pass


def run_gitleaks_scan(repository_path: Path) -> dict:
    report_path = repository_path.parent / "gitleaks-results.json"
    command = [
        "gitleaks",
        "detect",
        "--source",
        str(repository_path),
        "--report-format",
        "json",
        "--report-path",
        str(report_path),
        "--exit-code",
        "0",
        "--no-banner",
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
        raise ScannerExecutionError("GitLeaks executable was not found in the backend runtime.") from exc

    if result.returncode != 0:
        raise ScannerExecutionError(result.stderr.strip() or result.stdout.strip() or "GitLeaks scan failed.")

    findings_raw = []
    if report_path.exists() and report_path.read_text().strip():
        findings_raw = json.loads(report_path.read_text())

    findings = []
    for item in findings_raw:
        file_path = item.get("File")
        line_number = item.get("StartLine")
        findings.append(
            {
                "scanner_type": "gitleaks",
                "severity": "HIGH",
                "file_path": file_path,
                "line_number": line_number,
                "title": item.get("RuleID", "Secret detected"),
                "description": item.get("Description", "GitLeaks detected a potential secret."),
                "vulnerability_id": item.get("RuleID"),
                "raw_data": item,
            }
        )

    return {
        "findings_count": len(findings),
        "severity": "HIGH" if findings else "NONE",
        "findings": findings,
    }
