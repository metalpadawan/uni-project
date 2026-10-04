-- Keep the private path of the verified attendance photo for audit purposes.
ALTER TABLE attendance_records
    ADD COLUMN IF NOT EXISTS capture_path text;
