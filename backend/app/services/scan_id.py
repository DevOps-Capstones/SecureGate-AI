from datetime import datetime, timezone

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.scan import Scan


def generate_scan_id(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"SCAN-{today}-"
    latest_number = db.execute(
        select(func.max(func.cast(func.substring(Scan.scan_id, len(prefix) + 1), Integer)))
        .where(Scan.scan_id.like(f"{prefix}%"))
    ).scalar_one_or_none() or 0

    next_number = int(latest_number) + 1
    while True:
        candidate = f"{prefix}{next_number:04d}"
        exists = db.execute(select(Scan.id).where(Scan.scan_id == candidate)).scalar_one_or_none()
        if not exists:
            return candidate
        next_number += 1
