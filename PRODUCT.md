# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Three roles, one shared login screen that routes by role:
- **Admin** — creates lecturer/admin accounts, reviews and approves/rejects student self-registrations, enrols students directly, views system-wide rosters and course lists.
- **Lecturer** — sets up a weekly class schedule (which auto-opens/closes attendance sessions), starts/monitors a live attendance session and its rotating QR, sees who's enrolled in their courses.
- **Student** — registers their own account (pending admin approval) or is enrolled by an admin, checks in to open classes via face + QR, views their own attendance history.

Operating in a Nigerian public-university lecture-hall context (University of Cross River State) — in-person classes, one lecturer projecting/displaying a device to the room, students checking in on their own phone or laptop.

## Product Purpose

Prevent proxy/buddy attendance ("checking in" a friend who isn't physically present) in university lecture attendance, without making the honest, present student's check-in slow or effortful.

## Positioning

"Double-lock" attendance: a student is marked present only when a server-verified live face match **and** a short-lived, rotating, cryptographically signed classroom QR code both pass in the same attempt. Neither factor alone is sufficient — a stolen/screenshotted QR code doesn't work without the right live face behind it, and a photo or a stored embedding doesn't work without a currently-valid, in-room QR code. A simpler QR-only roster app, or a manual paper roll-call, cannot truthfully make this claim.

## Operating Context

- A lecturer either manually starts a session or one auto-opens on a pre-set weekly schedule; either way, the lecturer's own screen displays the rotating QR (refreshes every ~30s) for the room to see.
- A student opens their own check-in flow, captures live camera frames (no client-side ML — frames go to the server, which does all detection/matching), then scans or pastes the QR token.
- Face verification and QR validation both happen server-side; the browser never asserts or computes a match/liveness result itself.
- A rejected/mismatched attempt is logged for lecturer review rather than silently failing — the student can retry immediately.

## Capabilities and Constraints

- Stack: FastAPI (`api`) + a separate face-service (FastAPI + OpenCV YuNet/SFace, all face ML) + React/Vite frontend + PostgreSQL/pgvector in production (SQLite as a zero-config dev fallback).
- Role-based access (admin/lecturer/student) enforced server-side on every protected endpoint.
- Account creation always has a gate: admin-direct enrolment, or student self-registration held in an explicit pending-approval queue — never silent/automatic.
- Refresh tokens rotate and can be revoked; login and demo-login are rate-limited.
- Real deployment requires HTTPS (`getUserMedia`/camera access is blocked by browsers off `https://`/`localhost`) and `DEMO_MODE=false`.
- **Known gap, not yet built:** no course-enrolment management UI/API (who's enrolled in which course) — today that only happens via a demo-mode auto-enrolment shortcut or direct database access.
- **Explicitly out of scope:** fee/payment verification — no such system exists in this project.
- A non-camera fallback exists for QR entry (manual token paste) when automatic scanning isn't supported by the browser — worth preserving in any redesign, it's the accessibility/compatibility escape hatch for the check-in flow.

## Brand Commitments

- Product name: **SmartAttend**. Institution tag: **UNICROSS** (University of Cross River State), currently shown as a small caption under the logo.
- Existing logo mark: a face-scan icon (`ScanFace`) in a rounded square, paired with the wordmark "Smart" + accent-colored "Attend".
- No other binding visual constraints from the user — colors, typography, and overall visual world are open for this redesign (confirmed: the user asked for a redesign "to a more modern user interface," not a refresh preserving the current look).

## Evidence on Hand

No fabricated content. The existing implementation (all pages/components under `frontend/src`) is the incumbent system and the source of truth for current functionality — it is evidence, not a constraint, for this redesign.

## Product Principles

1. Attendance is only ever marked present when both factors independently pass — never a single-factor shortcut, even for convenience.
2. Trust decisions live entirely server-side; the client captures and displays, it never asserts identity or liveness itself.
3. Routine operation trends toward zero manual effort (scheduled auto-open/close) while staying fully overridable by a human.
4. Every new account has an explicit gate — human approval or admin action — never implicit trust.

## Accessibility & Inclusion

No formally required standard established. The camera-dependent check-in flow already has a manual-entry fallback for the QR step when automatic scanning isn't available — preserve an equivalent fallback path in any redesign rather than making the flow camera-only.
