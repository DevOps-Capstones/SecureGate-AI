from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    project_name: str = Field(..., examples=["payment-service"])
    repository_url: str = Field(..., examples=["https://github.com/company/payment-service"])
    branch: str = Field(default="main", examples=["main"])
    commit_sha: str = Field(..., examples=["abc123"])


class PipelineStartRequest(ScanCreate):
    pipeline_run_id: str = Field(..., examples=["9876543210"])


class PipelineCompleteRequest(BaseModel):
    scan_id: str = Field(..., examples=["SCAN-20260701-0001"])
    status: str = Field(..., examples=["SUCCESS"])


class ScanCreateResponse(BaseModel):
    scan_id: str = Field(examples=["SCAN-20260701-0001"])
    status: str = Field(examples=["RECEIVED"])


class ToolReportUploadResponse(BaseModel):
    scan_id: str
    tool: str
    status: str
    findings_count: int
    uploaded_at: datetime


class FindingResponse(BaseModel):
    tool: str
    severity: str
    title: str
    description: str | None = None
    file: str | None = None
    source_tool: str
    resolution_status: str = "PENDING"
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ToolReportResponse(BaseModel):
    tool_name: str
    status: str
    uploaded_at: datetime
    file_path: str | None = None
    scan_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ScanSummary(BaseModel):
    scan_id: str
    project_name: str
    repository_url: str
    image_name: str | None = None
    image_tag: str | None = None
    image_full_path: str | None = None
    branch: str
    commit_sha: str
    status: str
    pipeline_run_id: str | None = None
    pipeline_status: str | None = None
    received_at: datetime
    processing_at: datetime | None = None
    scoring_at: datetime | None = None
    report_generation_at: datetime | None = None
    notification_sent_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    security_score: int | None = None
    deployment_decision: str = "PENDING"
    sonar_quality_gate: str = "UNKNOWN"

    model_config = ConfigDict(from_attributes=True)


class TimelineEventResponse(BaseModel):
    label: str
    status: str
    timestamp: datetime | None = None


class NotificationResponse(BaseModel):
    notification_type: str
    category: str = "SCAN"
    severity_level: str = "INFO"
    summary_period: str | None = None
    recipient: str
    status: str
    created_at: datetime
    sent_at: datetime | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    action: str
    message: str
    actor: str
    created_at: datetime
    log_metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ScanDetailsResponse(ScanSummary):
    project_key: str | None = None
    uploaded_reports: list[ToolReportResponse]
    finding_counts: dict[str, int]
    tool_status: dict[str, str]
    findings: list[FindingResponse]
    timeline: list[TimelineEventResponse]
    notifications: list[NotificationResponse]
    audit_logs: list[AuditLogResponse]


class DashboardReportResponse(BaseModel):
    scan_id: str
    project_name: str
    report_type: str
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    total_projects: int
    active_project_name: str | None = None
    active_project_key: str | None = None
    active_repository_url: str | None = None
    total_scans: int
    active_scans: int
    recent_scans: list[ScanSummary]
    latest_uploads: list[ToolReportResponse]
    most_recent_findings: list[FindingResponse]
    latest_security_score: int | None
    latest_approval_status: str
    critical_findings: int
    high_findings: int
    medium_findings: int = 0
    low_findings: int = 0
    pending_findings: int
    resolved_findings: int
    vulnerability_trend: list[dict[str, Any]]
    score_trend: list[dict[str, Any]]
    recent_reports: list[DashboardReportResponse]
    recent_notifications: list[NotificationResponse]


class ToolReportPayload(BaseModel):
    payload: dict[str, Any] = Field(
        ...,
        description="Raw JSON report produced by GitHub Actions for the selected tool.",
        examples=[{"Results": []}],
    )
