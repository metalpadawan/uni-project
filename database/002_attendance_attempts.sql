-- Apply this migration to existing PostgreSQL deployments before running fix pass 7.
-- New Docker database volumes receive the same table from 001_initial.sql.
CREATE TABLE IF NOT EXISTS attendance_attempts (
    id varchar(36) PRIMARY KEY,
    session_id varchar(36) NOT NULL REFERENCES attendance_sessions(id),
    student_id varchar(36) NOT NULL REFERENCES students(id),
    face_match_score double precision NOT NULL,
    qr_token_id varchar(36) NOT NULL REFERENCES qr_tokens(id),
    attempted_at timestamptz NOT NULL,
    status attendance_status NOT NULL
);
