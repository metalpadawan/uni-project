# Build status

## Milestone 1 — core double-lock foundation

Implemented from the project build guide:

- Monorepo boundaries for frontend, API, face service, and database.
- PostgreSQL + pgvector production schema.
- Signed, server-stored QR tokens that expire after 30 seconds.
- Face matching service boundary with a documented distance threshold of `< 0.6` and mandatory liveness result.
- Atomic attendance endpoint that writes `present` only when both face and QR checks pass.
- Duplicate attendance protection and explicit recovery-oriented error messages.
- Docker Compose services for PostgreSQL, API, and face matching.

## Temporary deviations

- The existing React/Vite interface is retained in `frontend/` during the core-flow milestone instead of being immediately rewritten in Next.js. This avoids discarding the working UI before the API contract is connected. Migration to Next.js remains scheduled when the Student, Lecturer, and Admin route groups are introduced.
- Face capture is not yet connected to real camera landmarks. The face service currently receives 128-dimensional embeddings and performs the server-side distance calculation. Camera capture, quality checks, and blink/head-turn liveness are the next face-recognition task.
- SQLite is the API's zero-configuration development fallback. Docker and production configuration use PostgreSQL/pgvector as required by the guide.

## Fix pass 1

- Corrected CORS for the actual frontend URL on port 3000.
- Removed Docker's dependency on a missing `api/.env` file while keeping deployment values environment-overridable.
- Added consent-gated student face-template enrolment.
- Added server-generated QR images backed by signed 30-second tokens.
- Changed check-in input from a client-asserted face score to a 128-value captured embedding.
- The API now calls the face service for the authoritative distance and liveness decision.
- Valid-QR/failed-face attempts are persisted as `flagged` for lecturer review.
- Connected the frontend lecturer session and student check-in screens to the API client.

At the end of pass 1, authentication, schema alignment, course-enrolment validation, camera extraction, WebSockets, and end-to-end tests remained pending. Pass 2 addresses the first three items below.

## Fix pass 2

- Added Argon2 password hashing and signed access/refresh JWTs.
- Added one-time admin bootstrap, login, and admin-only account registration endpoints.
- Enforced Admin, Lecturer, and Student permissions on protected endpoints.
- Bound attendance sessions and QR rotation to the authenticated lecturer.
- Bound check-in to the authenticated student's profile instead of accepting a matric number from the client.
- Added course-enrolment and lecturer assignment models plus check-in validation.
- Added a local-only demo authentication path controlled by `DEMO_MODE`; production must set it to `false`.
- Updated the frontend API client to attach bearer tokens and use demo authentication for local portal switching.
- Added refresh-token exchange and per-client check-in rate limiting (5 attempts per minute).

At the end of pass 2, production login, refresh-token rotation/revocation, camera extraction, migrations, WebSockets, and end-to-end tests remained pending. Pass 3 addresses the login experience below.

## Fix pass 3

- Added a production email/password login screen with accessible labels, validation, loading state, and inline recovery errors.
- Persisted tokens and authenticated user details only for the current browser session.
- Derived the active portal from the authenticated JWT user role rather than a public selector.
- Added logout and cleared all session authentication material on exit.
- Kept local role shortcuts visibly separated and available only when `VITE_DEMO_MODE` is enabled.
- Added biometric privacy messaging to the login experience.

Still pending: real camera landmark extraction, refresh-token rotation/revocation, migration tooling, WebSocket live updates, account-administration screens, and complete end-to-end tests.

## Fix pass 4

- Removed unconditional demo login calls from lecturer session creation and student check-in; protected actions now use the currently authenticated account.
- Aligned the application model with the PostgreSQL schema: students link to user accounts, department and level live on the student profile, and face templates live only in `face_embeddings`.
- Added a portable embedding type that uses pgvector in PostgreSQL and JSON in the SQLite development fallback.
- Made lecturer ownership and student-account relationships mandatory and made face enrollment one-to-one per student.
- Expanded admin student enrollment to create the student login account and biometric template together.
- Verified the production frontend build, Docker Compose configuration, Python compilation, and frontend dependency audit.

This local dependency and test-environment limitation was resolved in fix pass 5.

## Fix pass 5

- Installed the pinned API dependencies, including pytest and pgvector, into `api/.venv`.
- Added repository-safe pytest path configuration in `api/pytest.ini`.
- Ran the QR signature and expiry unit tests successfully: 3 passed.

Next testing priority: integration coverage for the combined check-in endpoint with valid, expired, mismatched-face, duplicate, and wrong-role cases.

## Fix pass 6

- Enforced lecturer-course ownership before creating attendance sessions.
- Rejected check-ins after `ends_at` and capped QR expiry at the session end.
- Added authenticated, enrollment-filtered open-session discovery for students.
- Replaced the fixed development embedding with live browser face descriptors, camera permission recovery, and blink-based liveness.
- Added rear-camera QR scanning with a manual token fallback for browsers without `BarcodeDetector`.
- Added lecturer session closing, automatic 20-second QR rotation, and three-second live attendance polling.
- Added session ownership, discovery, expiry, successful dual-check, and face-mismatch regression tests.
- Lazy-loaded the face-recognition module so the main dashboard bundle remains small.

Intentional deviation: live lecturer updates currently use short polling instead of WebSockets. This keeps the end-to-end path simpler while preserving live behavior; WebSockets remain a scaling enhancement. Physical camera and QR scanning still require final testing on an HTTPS or localhost browser with camera hardware.

## Fix pass 7

- Moved failed face/liveness outcomes from `attendance_records` into a separate `attendance_attempts` audit trail.
- Kept `attendance_records` exclusively for successful, atomic face-and-QR attendance confirmation.
- Preserved lecturer visibility of flagged attempts while allowing a student to retry after a false mismatch.
- Added a regression test covering failed face verification followed by a valid retry using the same active QR token.
- Added `database/002_attendance_attempts.sql` for existing PostgreSQL deployments; new database volumes receive the table from the initial schema.

Implementation note: this pass follows the existing double-lock design in the repository. The external build guide referenced by `AGENTS.md` was unavailable locally; no intentional architectural deviation was made.
