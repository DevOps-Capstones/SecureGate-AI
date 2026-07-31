from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.scan import Notification
from app.schemas.scans import NotificationResponse
from app.services.auth import require_pipeline_api_key
from app.services.notifications import send_summary_notifications

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse], summary="List notification history")
def list_notifications(limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db)) -> list[Notification]:
    return list(db.execute(select(Notification).order_by(Notification.created_at.desc()).limit(limit)).scalars().all())


@router.post("/summary/{period}", response_model=list[NotificationResponse], summary="Send daily or weekly summary notifications", dependencies=[Depends(require_pipeline_api_key)])
def trigger_summary_notifications(period: Literal["daily", "weekly", "monthly"], db: Session = Depends(get_db)) -> list[Notification]:
    return send_summary_notifications(db, period)
