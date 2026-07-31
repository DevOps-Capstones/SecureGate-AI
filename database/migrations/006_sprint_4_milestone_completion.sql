-- Sprint 4 milestone completion: image tracking, finding resolution state, notification categorization.

ALTER TABLE scans ADD COLUMN IF NOT EXISTS image_name TEXT;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS image_tag VARCHAR(255);

ALTER TABLE findings ADD COLUMN IF NOT EXISTS resolution_status VARCHAR(30) NOT NULL DEFAULT 'PENDING';
ALTER TABLE findings ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(120);

ALTER TABLE notifications ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'SCAN';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS severity_level VARCHAR(30) NOT NULL DEFAULT 'INFO';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS summary_period VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_scans_image_name ON scans(image_name);
CREATE INDEX IF NOT EXISTS idx_findings_resolution_status ON findings(resolution_status);
CREATE INDEX IF NOT EXISTS idx_notifications_category ON notifications(category);
