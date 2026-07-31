from datetime import datetime
from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: str
    alert_id: str
    scan_id: str | None
    project_name: str
    repository: str | None
    branch: str | None
    severity: str
    alert_type: str
    status: str
    notification_channels: list[str]
    description: str
    recommendation: str
    runbook_url: str
    escalation_level: int
    escalation_history: list
    created_at: datetime
    resolved_at: datetime | None
    resolution_time: int | None

    model_config = {"from_attributes": True}


class AlertStatisticsResponse(BaseModel):
    total_alerts: int
    open_alerts: int
    resolved_alerts: int
    escalated_alerts: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_type: dict[str, int]


class AlertPolicyUpdate(BaseModel):
    enabled: bool = False
    slack_enabled: bool = True
    email_enabled: bool = True
    slack_min_severity: str = "LOW"
    email_min_severity: str = "HIGH"


class AlertPolicyResponse(AlertPolicyUpdate):
    project_key: str
    project_name: str
    repository_url: str
    updated_at: datetime | None = None
