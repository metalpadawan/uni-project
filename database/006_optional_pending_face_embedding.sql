-- Student account creation no longer requires an immediate camera capture.
-- Existing deployments need this before self-registration can store a pending
-- student record without a biometric template.
ALTER TABLE pending_students
    ALTER COLUMN face_embedding DROP NOT NULL;
