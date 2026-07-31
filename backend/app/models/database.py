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
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS image_name TEXT"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS image_tag VARCHAR(255)"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS image_full_path TEXT"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS branch VARCHAR(255) NOT NULL DEFAULT 'main'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS commit_sha VARCHAR(255) NOT NULL DEFAULT 'unknown'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS security_score INTEGER"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS deployment_decision VARCHAR(20) NOT NULL DEFAULT 'PENDING'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS sonar_quality_gate VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN'"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS pipeline_run_id VARCHAR(255)"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS pipeline_status VARCHAR(50)"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS processing_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS scoring_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS report_generation_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS notification_sent_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE tool_reports ADD COLUMN IF NOT EXISTS file_path TEXT"))
        connection.execute(text("ALTER TABLE findings ADD COLUMN IF NOT EXISTS resolution_status VARCHAR(30) NOT NULL DEFAULT 'PENDING'"))
        connection.execute(text("ALTER TABLE findings ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE findings ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(120)"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'SCAN'"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS severity_level VARCHAR(30) NOT NULL DEFAULT 'INFO'"))
        connection.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS summary_period VARCHAR(20)"))
        connection.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS actor VARCHAR(120) NOT NULL DEFAULT 'system'"))
        connection.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '{}'::jsonb"))
        connection.execute(text("ALTER TABLE scans ALTER COLUMN project_id DROP NOT NULL"))
        connection.execute(text("UPDATE scans SET project_name = COALESCE(project_name, repository_url, 'unknown-project') WHERE project_name IS NULL"))
        connection.execute(text("ALTER TABLE scans ALTER COLUMN project_name SET NOT NULL"))
        connection.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_key VARCHAR(100)"))
        connection.execute(text("UPDATE projects SET project_key = 'PRJ-LEGACY-' || LEFT(REPLACE(id::text, '-', ''), 8) WHERE project_key IS NULL"))
        connection.execute(text("ALTER TABLE projects ALTER COLUMN project_key SET NOT NULL"))
        connection.execute(text("UPDATE projects SET repository_url = regexp_replace(regexp_replace(lower(trim(repository_url)), '/$', ''), '\\.git$', '') WHERE repository_url IS NOT NULL"))
        connection.execute(text("""
            WITH ranked_projects AS (
                SELECT
                    id,
                    FIRST_VALUE(id) OVER (
                        PARTITION BY lower(repository_url)
                        ORDER BY created_at DESC, id DESC
                    ) AS keep_id
                FROM projects
            )
            UPDATE scans
            SET project_id = ranked_projects.keep_id
            FROM ranked_projects
            WHERE scans.project_id = ranked_projects.id
              AND ranked_projects.id <> ranked_projects.keep_id
        """))
        connection.execute(text("""
            UPDATE scans
            SET project_name = projects.name,
                repository_url = projects.repository_url
            FROM projects
            WHERE scans.project_id = projects.id
        """))
        connection.execute(text("""
            DELETE FROM projects
            USING (
                SELECT
                    id,
                    FIRST_VALUE(id) OVER (
                        PARTITION BY lower(repository_url)
                        ORDER BY created_at DESC, id DESC
                    ) AS keep_id
                FROM projects
            ) ranked_projects
            WHERE projects.id = ranked_projects.id
              AND ranked_projects.id <> ranked_projects.keep_id
        """))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_project_key ON projects(project_key)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_name_lower_unique ON projects(lower(name))"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_repository_url_lower_unique ON projects(lower(repository_url))"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_projects_repository_url ON projects(repository_url)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_scan_id ON scans(scan_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_received_at ON scans(received_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tool_reports_scan_pk ON tool_reports(scan_pk)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_findings_scan_pk ON findings(scan_pk)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_scan_pk ON audit_logs(scan_pk)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_decision ON scans(deployment_decision)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_pipeline_run_id ON scans(pipeline_run_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_image_name ON scans(image_name)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_image_full_path ON scans(image_full_path)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_findings_resolution_status ON findings(resolution_status)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_category ON notifications(category)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_scan_pk ON notifications(scan_pk)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_project_name ON alerts(project_name)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_alert_policies_project_id ON project_alert_policies(project_id)"))
        connection.execute(text("ALTER TABLE project_alert_policies ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE project_alert_policies ADD COLUMN IF NOT EXISTS slack_enabled BOOLEAN NOT NULL DEFAULT TRUE"))
        connection.execute(text("ALTER TABLE project_alert_policies ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN NOT NULL DEFAULT TRUE"))
        connection.execute(text("ALTER TABLE project_alert_policies ADD COLUMN IF NOT EXISTS slack_min_severity VARCHAR(30) NOT NULL DEFAULT 'LOW'"))
        connection.execute(text("ALTER TABLE project_alert_policies ADD COLUMN IF NOT EXISTS email_min_severity VARCHAR(30) NOT NULL DEFAULT 'HIGH'"))
        connection.execute(text("ALTER TABLE project_alert_policies ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
