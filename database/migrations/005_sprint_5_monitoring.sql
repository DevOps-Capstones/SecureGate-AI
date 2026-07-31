CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(120) UNIQUE NOT NULL,
    scan_pk UUID NULL REFERENCES scans(id) ON DELETE SET NULL,
    scan_id VARCHAR(100),
    project_name VARCHAR(255) NOT NULL,
    repository TEXT,
    branch VARCHAR(255),
    severity VARCHAR(30) NOT NULL,
    alert_type VARCHAR(120) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    notification_channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    runbook_url TEXT NOT NULL DEFAULT 'https://runbooks.example.com/securegate',
    escalation_level INTEGER NOT NULL DEFAULT 0,
    escalation_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_time INTEGER
);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_project_name ON alerts(project_name);
