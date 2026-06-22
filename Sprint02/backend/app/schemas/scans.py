from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    repository_url: str = Field(
        ...,
        examples=["https://github.com/org/project"],
        description="Git repository URL to clone and scan.",
    )


class ScanCreateResponse(BaseModel):
    scan_id: str = Field(examples=["SCAN-20260622-0001"])
    status: str = Field(examples=["PASSED"])
    deployment_approved: bool = Field(examples=[True])
    critical_count: int = Field(examples=[0])
    high_count: int = Field(examples=[3])
    medium_count: int = Field(examples=[8])
    secrets_count: int = Field(examples=[0])


class FindingResponse(BaseModel):
    scanner_type: str
    severity: str
    file_path: str | None = None
    line_number: int | None = None
    title: str | None = None
    description: str | None = None
    vulnerability_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ScanSummary(BaseModel):
    scan_id: str
    repository_url: str
    status: str
    deployment_approved: bool
    started_at: datetime
    completed_at: datetime | None = None
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    secrets_count: int

    model_config = ConfigDict(from_attributes=True)


class ScanDetailsResponse(ScanSummary):
    gitleaks_findings: list[FindingResponse]
    trivy_findings: list[FindingResponse]
