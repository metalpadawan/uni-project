-- Apply this migration to existing PostgreSQL deployments before running fix pass A.
-- New Docker database volumes receive the same table from 001_initial.sql.
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id varchar(36) PRIMARY KEY,
    user_id varchar(36) NOT NULL REFERENCES users(id),
    token_hash text UNIQUE NOT NULL,
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);
