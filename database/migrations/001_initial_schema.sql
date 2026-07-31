CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    repository_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id VARCHAR(100) NOT NULL UNIQUE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    project_name VARCHAR(255) NOT NULL,
    repository_url TEXT NOT NULL,
    branch VARCHAR(255) NOT NULL DEFAULT 'main',
    commit_sha VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'RECEIVED',
    security_score INTEGER,
    deployment_decision VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    sonar_quality_gate VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN',
    evaluated_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    report_type VARCHAR(100) NOT NULL,
    file_path TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_pk UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    tool_name VARCHAR(80) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'UPLOADED',
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_pk UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    tool_report_pk UUID REFERENCES tool_reports(id) ON DELETE CASCADE,
    tool VARCHAR(80) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    file TEXT,
    source_tool VARCHAR(100) NOT NULL,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_pk UUID REFERENCES scans(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    log_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scans_project_id ON scans(project_id);
CREATE INDEX IF NOT EXISTS idx_scans_scan_id ON scans(scan_id);
CREATE INDEX IF NOT EXISTS idx_scans_received_at ON scans(received_at);
CREATE INDEX IF NOT EXISTS idx_reports_scan_id ON reports(scan_id);
CREATE INDEX IF NOT EXISTS idx_tool_reports_scan_pk ON tool_reports(scan_pk);
CREATE INDEX IF NOT EXISTS idx_findings_scan_pk ON findings(scan_pk);
CREATE INDEX IF NOT EXISTS idx_audit_logs_scan_pk ON audit_logs(scan_pk);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
CREATE INDEX IF NOT EXISTS idx_scans_decision ON scans(deployment_decision);
