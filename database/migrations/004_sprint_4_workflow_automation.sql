-- Sprint 4: DevSecOps workflow automation, lifecycle tracking, notifications, and file-backed reports.

ALTER TABLE scans ADD COLUMN IF NOT EXISTS pipeline_run_id VARCHAR(255);
ALTER TABLE scans ADD COLUMN IF NOT EXISTS pipeline_status VARCHAR(50);
ALTER TABLE scans ADD COLUMN IF NOT EXISTS processing_at TIMESTAMPTZ;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS scoring_at TIMESTAMPTZ;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS report_generation_at TIMESTAMPTZ;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS notification_sent_at TIMESTAMPTZ;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;

ALTER TABLE tool_reports ADD COLUMN IF NOT EXISTS file_path TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS actor VARCHAR(120) NOT NULL DEFAULT 'system';

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_pk UUID REFERENCES scans(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    recipient TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    message TEXT NOT NULL,
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scans_pipeline_run_id ON scans(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_notifications_scan_pk ON notifications(scan_pk);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
