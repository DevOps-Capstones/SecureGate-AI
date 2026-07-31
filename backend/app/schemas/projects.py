from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.scans import ScanSummary


class ProjectCreate(BaseModel):
    name: str = Field(..., examples=["securegate-demo-app"])
    repository_url: str = Field(..., examples=["https://github.com/company/securegate-demo-app"])


class ProjectResponse(BaseModel):
    project_key: str
    name: str
    repository_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolHealthResponse(BaseModel):
    tool: str
    label: str
    status: str
    critical: int
    high: int
    medium: int
    low: int


class ProjectHealthResponse(ProjectResponse):
    latest_scan: ScanSummary | None = None
    total_scans: int
    latest_security_score: int | None = None
    latest_decision: str
    sonar_quality_gate: str
    severity_counts: dict[str, int]
    decision_counts: dict[str, int]
    tool_health: list[ToolHealthResponse]
    recent_scans: list[ScanSummary]


class ProjectFindingResponse(BaseModel):
    tool: str
    severity: str
    title: str
    description: str | None = None
    file: str | None = None
    source_tool: str
    first_seen_scan_id: str
    first_seen_at: datetime
    latest_seen_scan_id: str
    latest_seen_at: datetime
    occurrences: int
    resolution_status: str
    resolved_at: datetime | None = None


class ProjectTriggerScanRequest(BaseModel):
    runner: str = Field(default="github-actions", examples=["github-actions"])
    branch: str = Field(default="main", examples=["main"])


class ProjectTriggerScanResponse(BaseModel):
    status: str
    runner: str
    workflow_file: str
    branch: str
    repository: str
    message: str
