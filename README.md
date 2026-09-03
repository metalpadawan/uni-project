# SmartAttend

Multi-authentication attendance platform for the University of Cross River State. Attendance is recorded only when server-side face verification and a short-lived session QR both pass.

## What's built

- `frontend` (React/Vite), `api` (FastAPI), `face-service` (FastAPI + OpenCV), `database` (PostgreSQL/pgvector schema + migrations).
- Auth: Argon2 password hashing, signed access/refresh JWTs with refresh-token rotation and revocation, role-based access (admin/lecturer/student), rate-limited login.
- Attendance: signed 30-second rotating QR tokens, atomic check-in that only marks a student present when both the QR and a server-side face match pass, failed attempts audited separately for lecturer review.
- Face verification: `face-service` does its own detection and recognition (OpenCV's YuNet detector + SFace recognizer) from captured camera frames — the browser never computes or asserts anything about a match itself, it only captures frames.
- Scheduling: recurring weekly class slots that auto-open and auto-close attendance sessions.
- Accounts: admin-created lecturer/admin accounts, admin-driven student enrolment, and student self-registration with an admin approval queue.

## Run locally (native, no Docker)

```powershell
# api
cd api
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv
$env:DEMO_MODE = "true"
.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# face-service (separate venv — different dependency set)
cd face-service
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv
.venv\Scripts\python.exe -m uvicorn main:app --port 8001 --reload

# frontend
cd frontend
npm install
npm run dev -- --port 3000
```

`http://127.0.0.1:8000/docs` has the interactive API. The api defaults to a zero-config SQLite file (`api/smart_attendance.db`) when `DATABASE_URL` isn't set — fine for local development, not for anything real (see below).

## Run with Docker Compose (PostgreSQL/pgvector)

```
docker compose up
```

This is the path a real deployment should use — `api`'s SQLite fallback has no place outside local development. `db`'s healthcheck gates `api`'s startup so it doesn't race Postgres's own initialization on a fresh volume.

## Before deploying anywhere real

- **Set `DEMO_MODE=false`.** It defaults to `false` already, but `docker-compose.yml` and local dev scripts override it to `true` for convenience — make sure that override doesn't follow you to a real deployment. With it on, `POST /auth/demo/{role}` hands out a valid admin token to anyone, no credentials required.
- **Rotate `JWT_SECRET` and `QR_SIGNING_SECRET`** to real random values. The api refuses to start with `DEMO_MODE=false` and either secret still at its development-placeholder value, so this is enforced, not just documented — but only once demo mode is actually off.
- **Serve over HTTPS.** `getUserMedia` (camera access, used for face check-in/enrolment) is blocked by browsers on any origin that isn't `https://` or `localhost`. This only matters once the frontend is reachable somewhere other than a developer's own machine — set up TLS termination (a reverse proxy, load balancer, or platform-provided HTTPS) in front of wherever the frontend and api actually get deployed.
- **Re-enrol everyone** if this is following an earlier deployment that predates the server-side face-verification rewrite — face templates from the old client-side pipeline aren't compatible with the current one.
