from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.scan import Scan, ScanFinding
from app.services.gitleaks import ScannerExecutionError, run_gitleaks_scan
from app.services.repository import RepositoryCloneError, clone_repository, normalize_repository_url
from app.services.scan_id import generate_scan_id
from app.services.security_gate import evaluate_security_gate
from app.services.trivy import run_trivy_fs_scan


def _store_findings(db: Session, scan: Scan, findings: list[dict]) -> None:
    for finding in findings:
        db.add(
            ScanFinding(
                scan_pk=scan.id,
                scanner_type=finding["scanner_type"],
                severity=finding["severity"],
                file_path=finding.get("file_path"),
                line_number=finding.get("line_number"),
                title=finding.get("title"),
                description=finding.get("description"),
                vulnerability_id=finding.get("vulnerability_id"),
                raw_data=finding.get("raw_data", {}),
            )
        )


def run_repository_scan(db: Session, repository_url: str) -> Scan:
    normalized_url = normalize_repository_url(repository_url)
    scan = Scan(
        scan_id=generate_scan_id(db),
        repository_url=normalized_url,
        status="RUNNING",
        deployment_approved=False,
        started_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        repository_path = clone_repository(normalized_url, scan.scan_id)
        gitleaks_result = run_gitleaks_scan(repository_path)
        trivy_result = run_trivy_fs_scan(repository_path)

        secrets_count = gitleaks_result["findings_count"]
        gate = evaluate_security_gate(
            secrets_count=secrets_count,
            critical_count=trivy_result["critical_count"],
        )

        scan.secrets_count = secrets_count
        scan.critical_count = trivy_result["critical_count"]
        scan.high_count = trivy_result["high_count"]
        scan.medium_count = trivy_result["medium_count"]
        scan.low_count = trivy_result["low_count"]
        scan.deployment_approved = gate["deployment_approved"]
        scan.status = "PASSED" if scan.deployment_approved else "FAILED"
        scan.completed_at = datetime.now(timezone.utc)

        _store_findings(db, scan, gitleaks_result["findings"])
        _store_findings(db, scan, trivy_result["findings"])
        db.commit()
        db.refresh(scan)
        return scan
    except (RepositoryCloneError, ScannerExecutionError, TimeoutError, ValueError) as exc:
        scan.status = "ERROR"
        scan.deployment_approved = False
        scan.completed_at = datetime.now(timezone.utc)
        db.add(
            ScanFinding(
                scan_pk=scan.id,
                scanner_type="system",
                severity="ERROR",
                title="Scan execution failed",
                description=str(exc),
                raw_data={"error": str(exc)},
            )
        )
        db.commit()
        db.refresh(scan)
        return scan
