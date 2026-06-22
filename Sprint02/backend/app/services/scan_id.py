from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scan import Scan


def generate_scan_id(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"SCAN-{today}-"
    latest_scan_id = db.execute(
        select(Scan.scan_id)
        .where(Scan.scan_id.like(f"{prefix}%"))
        .order_by(Scan.scan_id.desc())
        .limit(1)
    ).scalar_one_or_none()

    next_number = 1
    if latest_scan_id:
        next_number = int(latest_scan_id.rsplit("-", 1)[-1]) + 1

    return f"{prefix}{next_number:04d}"
