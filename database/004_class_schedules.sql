-- Apply this migration to existing PostgreSQL deployments before running the scheduling fix pass.
-- New Docker database volumes receive the same table from 001_initial.sql.
CREATE TABLE IF NOT EXISTS class_schedules (
    id varchar(36) PRIMARY KEY,
    course_id varchar(36) NOT NULL REFERENCES courses(id),
    day_of_week int NOT NULL,
    start_time time NOT NULL,
    duration_minutes int NOT NULL
);
