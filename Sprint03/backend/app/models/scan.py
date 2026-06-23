from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scans: Mapped[list["Scan"]] = relationship(back_populates="project")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    scan_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_url: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="RECEIVED")
    security_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deployment_decision: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    sonar_quality_gate: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped[Project | None] = relationship(back_populates="scans")
    tool_reports: Mapped[list["ToolReport"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    findings: Mapped[list["Finding"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="scan", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    scan_pk: Mapped[str] = mapped_column("scan_id", UUID(as_uuid=False), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan: Mapped[Scan] = relationship(back_populates="reports")


class ToolReport(Base):
    __tablename__ = "tool_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    scan_pk: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="UPLOADED")
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan: Mapped[Scan] = relationship(back_populates="tool_reports")
    findings: Mapped[list["Finding"]] = relationship(back_populates="tool_report", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    scan_pk: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    tool_report_pk: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tool_reports.id", ondelete="CASCADE"), nullable=True)
    tool: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_tool: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan: Mapped[Scan] = relationship(back_populates="findings")
    tool_report: Mapped[ToolReport | None] = relationship(back_populates="findings")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid())
    scan_pk: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("scans.id", ondelete="CASCADE"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    log_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan: Mapped[Scan | None] = relationship(back_populates="audit_logs")
