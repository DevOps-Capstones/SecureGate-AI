-- Sprint 4 Docker Hub artifact tracking
ALTER TABLE scans ADD COLUMN IF NOT EXISTS image_full_path TEXT;
CREATE INDEX IF NOT EXISTS idx_scans_image_full_path ON scans(image_full_path);
UPDATE scans
SET image_full_path = CASE
    WHEN image_name IS NOT NULL AND image_tag IS NOT NULL THEN image_name || ':' || image_tag
    WHEN image_name IS NOT NULL THEN image_name
    ELSE image_full_path
END
WHERE image_full_path IS NULL;
