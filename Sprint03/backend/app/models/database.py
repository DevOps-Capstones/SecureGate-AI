from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.models.scan import Base

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS project_name VARCHAR(255)"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS repository_url TEXT"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS branch VARCHAR(255) NOT NULL DEFAULT 'main'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS commit_sha VARCHAR(255) NOT NULL DEFAULT 'unknown'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS security_score INTEGER"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS deployment_decision VARCHAR(20) NOT NULL DEFAULT 'PENDING'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS sonar_quality_gate VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '{}'::jsonb"))
        connection.execute(text("ALTER TABLE scans ALTER COLUMN project_id DROP NOT NULL"))
        connection.execute(text("UPDATE scans SET project_name = COALESCE(project_name, repository_url, 'unknown-project') WHERE project_name IS NULL"))
        connection.execute(text("ALTER TABLE scans ALTER COLUMN project_name SET NOT NULL"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_scan_id ON scans(scan_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_received_at ON scans(received_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tool_reports_scan_pk ON tool_reports(scan_pk)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_findings_scan_pk ON findings(scan_pk)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_scan_pk ON audit_logs(scan_pk)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_decision ON scans(deployment_decision)"))
