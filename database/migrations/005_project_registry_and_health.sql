-- Sprint project registry and project-health support.
-- Adds stable SecureGate AI project IDs for one-repository-per-project tracking.

ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_key VARCHAR(100);

UPDATE projects
SET project_key = 'PRJ-LEGACY-' || LEFT(REPLACE(id::text, '-', ''), 8)
WHERE project_key IS NULL;

ALTER TABLE projects ALTER COLUMN project_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_project_key ON projects(project_key);
CREATE INDEX IF NOT EXISTS idx_projects_repository_url ON projects(repository_url);
