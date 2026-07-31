from datetime import datetime, timezone
from urllib import request

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.database import get_db

router = APIRouter(tags=["health"])
STARTED_AT = datetime.now(timezone.utc)


def _uptime() -> int:
    return int((datetime.now(timezone.utc) - STARTED_AT).total_seconds())


def _external_health(url: str) -> dict:
    try:
        with request.urlopen(url, timeout=3) as response:
            return {"status": "healthy" if response.status < 500 else "warning", "uptime_seconds": _uptime()}
    except Exception as exc:
        return {"status": "critical", "uptime_seconds": _uptime(), "error": str(exc)}


@router.get("/health")
def health_check() -> dict[str, str | int]:
    return {"status": "healthy", "uptime_seconds": _uptime()}


@router.get("/health/database")
def database_health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "uptime_seconds": _uptime()}
    except Exception as exc:
        return {"status": "critical", "uptime_seconds": _uptime(), "error": str(exc)}


@router.get("/health/prometheus")
def prometheus_health() -> dict:
    return _external_health("http://prometheus:9090/-/healthy")


@router.get("/health/grafana")
def grafana_health() -> dict:
    return _external_health("http://grafana:3000/api/health")


@router.get("/health/sonarqube")
def sonarqube_health() -> dict:
    return _external_health("http://sonarqube:9000/api/system/status")
