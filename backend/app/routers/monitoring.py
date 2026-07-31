from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.scan import Alert, Finding, Notification, Project, Report, Scan
from app.services.alerts import alert_statistics, notification_analytics

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


def _since(range_name: str) -> datetime:
    now = datetime.now(timezone.utc)
    return {"24h": now - timedelta(days=1), "7d": now - timedelta(days=7), "30d": now - timedelta(days=30), "90d": now - timedelta(days=90), "12m": now - timedelta(days=365)}.get(range_name, now - timedelta(days=30))


@router.get("/overview", summary="Security operations overview")
def monitoring_overview(db: Session = Depends(get_db)) -> dict:
    scans = db.execute(select(Scan)).scalars().all()
    findings = db.execute(select(Finding)).scalars().all()
    reports = db.execute(select(Report)).scalars().all()
    latest_scan = max(scans, key=lambda item: item.received_at, default=None)
    completed = [scan for scan in scans if scan.completed_at and scan.received_at]
    avg_scan_time = round(sum((scan.completed_at - scan.received_at).total_seconds() for scan in completed) / len(completed), 2) if completed else 0
    approval_rate = round((sum(1 for scan in scans if scan.deployment_decision == "APPROVED") / len(scans)) * 100, 2) if scans else 0
    risk_projects = Counter(finding.scan.project_name for finding in findings if finding.severity.upper() in {"CRITICAL", "HIGH"} and finding.scan)
    return {
        "security_score": latest_scan.security_score if latest_scan else None,
        "deployment_approval_rate": approval_rate,
        "critical_findings": sum(1 for item in findings if item.severity.upper() == "CRITICAL"),
        "high_findings": sum(1 for item in findings if item.severity.upper() == "HIGH"),
        "running_scans": sum(1 for scan in scans if scan.status in {"RECEIVED", "PROCESSING", "SCORING", "REPORT_GENERATION"}),
        "completed_scans": sum(1 for scan in scans if scan.status == "COMPLETED"),
        "failed_scans": sum(1 for scan in scans if scan.status == "FAILED"),
        "reports_generated": len(reports),
        "average_scan_time": avg_scan_time,
        "top_risk_projects": [{"project": name, "risk_findings": count} for name, count in risk_projects.most_common(5)],
        "alerts": alert_statistics(db),
        "notifications": notification_analytics(db),
    }


@router.get("/analytics", summary="Historical security analytics")
def historical_analytics(range: str = Query(default="30d"), db: Session = Depends(get_db)) -> dict:
    since = _since(range)
    scans = db.execute(select(Scan).where(Scan.received_at >= since).order_by(Scan.received_at)).scalars().all()
    scan_ids = [scan.id for scan in scans]
    findings = db.execute(select(Finding).where(Finding.scan_pk.in_(scan_ids))).scalars().all() if scan_ids else []
    buckets: dict[str, dict] = defaultdict(lambda: {"scans": 0, "approved": 0, "rejected": 0, "score_total": 0, "score_count": 0, "critical": 0, "high": 0, "secrets": 0})
    scan_bucket = {}
    for scan in scans:
        key = scan.received_at.date().isoformat()
        scan_bucket[scan.id] = key
        buckets[key]["scans"] += 1
        if scan.deployment_decision == "APPROVED": buckets[key]["approved"] += 1
        if scan.deployment_decision == "REJECTED": buckets[key]["rejected"] += 1
        if scan.security_score is not None:
            buckets[key]["score_total"] += scan.security_score
            buckets[key]["score_count"] += 1
    for finding in findings:
        key = scan_bucket.get(finding.scan_pk)
        if not key: continue
        if finding.severity.upper() == "CRITICAL": buckets[key]["critical"] += 1
        if finding.severity.upper() == "HIGH": buckets[key]["high"] += 1
        if finding.tool == "gitleaks": buckets[key]["secrets"] += 1
    trend = []
    for date, data in sorted(buckets.items()):
        trend.append({**data, "date": date, "average_score": round(data["score_total"] / data["score_count"], 2) if data["score_count"] else None})
    return {"range": range, "trend": trend}


@router.get("/widgets", summary="Reusable monitoring widgets")
def monitoring_widgets(db: Session = Depends(get_db)) -> dict:
    scans = db.execute(select(Scan).order_by(Scan.received_at.desc()).limit(1)).scalars().all()
    latest = scans[0] if scans else None
    findings = db.execute(select(Finding)).scalars().all()
    notifications = notification_analytics(db)
    return {
        "current_security_score": latest.security_score if latest else None,
        "latest_scan": latest.scan_id if latest else None,
        "critical_findings": sum(1 for f in findings if f.severity.upper() == "CRITICAL"),
        "deployment_status": latest.deployment_decision if latest else "PENDING",
        "notification_status": f"{notifications['notification_success_rate']}% success",
        "api_health": "Healthy",
        "recent_alerts": alert_statistics(db).get("open_alerts", 0),
        "average_scan_time": monitoring_overview(db)["average_scan_time"],
    }
