from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.scan import Alert, Project, ProjectAlertPolicy
from app.schemas.alerts import AlertPolicyResponse, AlertPolicyUpdate, AlertResponse, AlertStatisticsResponse
from app.services.alerts import alert_statistics, escalate_open_alerts, process_alertmanager_webhook
from app.services.alert_policies import normalize_severity, project_policy_response

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse], summary="List alerts")
def list_alerts(
    severity: str | None = None,
    status: str | None = None,
    project: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Alert]:
    escalate_open_alerts(db)
    query = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if severity:
        query = query.where(Alert.severity == severity.upper())
    if status:
        query = query.where(Alert.status == status.upper())
    if project:
        query = query.where(Alert.project_name.ilike(f"%{project}%"))
    db.commit()
    return list(db.execute(query).scalars().all())


@router.get("/history", response_model=list[AlertResponse], summary="List alert history")
def alert_history(db: Session = Depends(get_db)) -> list[Alert]:
    return list(db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(500)).scalars().all())


@router.get("/statistics", response_model=AlertStatisticsResponse, summary="Get alert statistics")
def get_alert_statistics(db: Session = Depends(get_db)) -> AlertStatisticsResponse:
    return AlertStatisticsResponse(**alert_statistics(db))


@router.get("/policies/{project_key}", response_model=AlertPolicyResponse, summary="Get project alert override policy")
def get_project_alert_policy(project_key: str, db: Session = Depends(get_db)) -> dict:
    project = db.execute(select(Project).where(Project.project_key == project_key)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    policy = db.execute(select(ProjectAlertPolicy).where(ProjectAlertPolicy.project_id == project.id)).scalar_one_or_none()
    return project_policy_response(project, policy)


@router.put("/policies/{project_key}", response_model=AlertPolicyResponse, summary="Save project alert override policy")
def update_project_alert_policy(project_key: str, payload: AlertPolicyUpdate, db: Session = Depends(get_db)) -> dict:
    project = db.execute(select(Project).where(Project.project_key == project_key)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    policy = db.execute(select(ProjectAlertPolicy).where(ProjectAlertPolicy.project_id == project.id)).scalar_one_or_none()
    if not policy:
        policy = ProjectAlertPolicy(project_id=project.id)
        db.add(policy)
    policy.enabled = payload.enabled
    policy.slack_enabled = payload.slack_enabled
    policy.email_enabled = payload.email_enabled
    policy.slack_min_severity = normalize_severity(payload.slack_min_severity, "LOW")
    policy.email_min_severity = normalize_severity(payload.email_min_severity, "HIGH")
    db.commit()
    db.refresh(policy)
    return project_policy_response(project, policy)


@router.get("/{alert_id}", response_model=AlertResponse, summary="Get alert details")
def get_alert(alert_id: str, db: Session = Depends(get_db)) -> Alert:
    alert = db.execute(select(Alert).where((Alert.alert_id == alert_id) | (Alert.id == alert_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/webhook-placeholder", summary="Receive Alertmanager webhook")
def alertmanager_webhook_placeholder(payload: dict, db: Session = Depends(get_db)) -> dict:
    return process_alertmanager_webhook(db, payload)
