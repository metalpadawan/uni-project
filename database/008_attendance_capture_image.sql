-- Free Render services have an ephemeral filesystem. Keep the verified
-- attendance image in Postgres alongside its private logical folder path.
ALTER TABLE attendance_records
    ADD COLUMN IF NOT EXISTS capture_image bytea;
