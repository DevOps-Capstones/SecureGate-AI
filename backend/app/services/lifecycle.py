from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.scan import AuditLog, Scan

STATUS_TIMESTAMP_FIELDS = {
    "PROCESSING": "processing_at",
    "SCORING": "scoring_at",
    "REPORT_GENERATION": "report_generation_at",
    "NOTIFICATION_SENT": "notification_sent_at",
    "COMPLETED": "completed_at",
    "FAILED": "failed_at",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def set_scan_status(db: Session, scan: Scan, status: str, message: str, metadata: dict | None = None, actor: str = "system") -> None:
    scan.status = status
    timestamp_field = STATUS_TIMESTAMP_FIELDS.get(status)
    if timestamp_field and getattr(scan, timestamp_field, None) is None:
        setattr(scan, timestamp_field, utcnow())
    db.add(AuditLog(scan_pk=scan.id, action=f"STATUS_{status}", message=message, actor=actor, log_metadata=metadata or {}))
