CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE scans ADD COLUMN IF NOT EXISTS project_name VARCHAR(255);
ALTER TABLE scans ADD COLUMN IF NOT EXISTS repository_url TEXT;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS branch VARCHAR(255) NOT NULL DEFAULT 'main';
ALTER TABLE scans ADD COLUMN IF NOT EXISTS commit_sha VARCHAR(255) NOT NULL DEFAULT 'unknown';
ALTER TABLE scans ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE scans ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE scans ALTER COLUMN project_id DROP NOT NULL;
UPDATE scans SET project_name = COALESCE(project_name, repository_url, 'unknown-project') WHERE project_name IS NULL;
ALTER TABLE scans ALTER COLUMN project_name SET NOT NULL;

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

CREATE INDEX IF NOT EXISTS idx_scans_scan_id ON scans(scan_id);
CREATE INDEX IF NOT EXISTS idx_scans_received_at ON scans(received_at);
CREATE INDEX IF NOT EXISTS idx_tool_reports_scan_pk ON tool_reports(scan_pk);
CREATE INDEX IF NOT EXISTS idx_findings_scan_pk ON findings(scan_pk);
CREATE INDEX IF NOT EXISTS idx_audit_logs_scan_pk ON audit_logs(scan_pk);
