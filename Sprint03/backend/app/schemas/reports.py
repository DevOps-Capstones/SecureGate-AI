from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReportHistoryResponse(BaseModel):
    scan_id: str
    project_name: str
    branch: str
    report_type: str
    decision: str
    security_score: int | None
    critical_count: int
    high_count: int
    created_at: datetime


class MasterReportResponse(BaseModel):
    executive_summary: dict[str, Any]
    security_score: dict[str, Any] = Field(
        examples=[{"score": 84, "maximum": 100, "passing_score": 80, "deductions": {"critical": 15, "high": 8, "medium": 3}}]
    )
    deployment_decision: dict[str, Any] = Field(examples=[{"decision": "APPROVED", "reasons": []}])
    vulnerability_summary: dict[str, Any]
    tool_findings_summary: dict[str, Any]
    finding_counts: dict[str, int]
    recommendations: list[dict[str, Any]]
    report_metadata: dict[str, Any]

    model_config = ConfigDict(extra="allow")
