from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    project_name: str = Field(..., examples=["payment-service"])
    repository_url: str = Field(..., examples=["https://github.com/company/payment-service"])
    branch: str = Field(default="main", examples=["main"])
    commit_sha: str = Field(..., examples=["abc123"])


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

    model_config = ConfigDict(from_attributes=True)


class ToolReportResponse(BaseModel):
    tool_name: str
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanSummary(BaseModel):
    scan_id: str
    project_name: str
    repository_url: str
    branch: str
    commit_sha: str
    status: str
    received_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ScanDetailsResponse(ScanSummary):
    uploaded_reports: list[ToolReportResponse]
    finding_counts: dict[str, int]
    tool_status: dict[str, str]
    findings: list[FindingResponse]


class DashboardSummaryResponse(BaseModel):
    total_projects: int
    total_scans: int
    recent_scans: list[ScanSummary]
    latest_uploads: list[ToolReportResponse]
    most_recent_findings: list[FindingResponse]


class ToolReportPayload(BaseModel):
    payload: dict[str, Any] = Field(
        ...,
        description="Raw JSON report produced by GitHub Actions for the selected tool.",
        examples=[{"Results": []}],
    )
