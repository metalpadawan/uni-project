-- Apply this migration to existing PostgreSQL deployments before running the self-registration fix pass.
-- New Docker database volumes receive the same table from 001_initial.sql.
DO $$ BEGIN
    CREATE TYPE registration_status AS ENUM ('pending','approved','rejected');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS pending_students (
    id varchar(36) PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    matric_no text NOT NULL,
    department text NOT NULL,
    level int NOT NULL,
    face_embedding vector(128) NOT NULL,
    biometric_consent boolean NOT NULL,
    status registration_status NOT NULL DEFAULT 'pending',
    requested_at timestamptz NOT NULL,
    reviewed_at timestamptz,
    reviewed_by varchar(36) REFERENCES users(id),
    rejection_reason text
);
