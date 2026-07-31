import json
from pathlib import Path
from typing import Any

from app.config.settings import settings

REPORT_FILENAMES = {
    "gitleaks": "gitleaks-report.json",
    "trivy-fs": "trivy-fs-report.json",
    "trivy-image": "trivy-image-report.json",
    "semgrep": "semgrep-report.json",
    "sonarqube": "sonarqube-report.json",
    "unit-tests": "unit-tests-report.json",
    "PDF": "deployment_approval.pdf",
    "DOCX": "deployment_approval.docx",
    "JSON": "deployment_approval.json",
    "AI_SUMMARY": "ai_summary.json",
    "AI_REMEDIATION": "ai_remediation_plan.json",
    "AI_SUMMARY_PDF": "AI_Summary_Report.pdf",
    "AI_REMEDIATION_PDF": "AI_Remediation_Plan.pdf",
}


def scan_storage_dir(scan_id: str) -> Path:
    path = Path(settings.storage_root) / "scans" / scan_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def stored_report_path(scan_id: str, report_type: str) -> Path:
    filename = REPORT_FILENAMES[report_type]
    return scan_storage_dir(scan_id) / filename


def save_json_report(scan_id: str, report_type: str, payload: dict[str, Any] | list[Any]) -> str:
    path = stored_report_path(scan_id, report_type)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path)


def save_binary_report(scan_id: str, report_type: str, content: bytes) -> str:
    path = stored_report_path(scan_id, report_type)
    path.write_bytes(content)
    return str(path)


def report_exists(scan_id: str, report_type: str) -> bool:
    return stored_report_path(scan_id, report_type).exists()
