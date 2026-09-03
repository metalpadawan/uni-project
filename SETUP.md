# SmartAttend — Setup Guide

This walks through getting SmartAttend running from a fresh `git clone`, on three paths: **Docker Compose** (fewer moving parts, recommended if you just want it running locally), **native/uv** (what this project was actually developed and tested against, and what you need if you're going to develop on it), or **Vercel + Render** (a real public URL, for demos/coursework submission). All three are covered fully below.

The system has three services:

| Service | What it is | Port |
|---|---|---|
| `frontend` | React/Vite web app | 3000 |
| `api` | FastAPI backend — auth, courses, sessions, attendance | 8000 |
| `face-service` | FastAPI face-detection/verification microservice | 8001 |
| `db` | PostgreSQL + pgvector (native path can substitute SQLite) | 5432 |

> The repository root itself is not a website — if you open this folder directly in a browser or point a generic static file server at it, you'll just see a directory listing. The frontend has to be started (`npm run dev`, from the steps below) and opened at the URL that command prints, not by browsing the folder.

---

## Path A: Docker Compose (recommended for just running it)

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin) installed and running.
- Node.js 18+ (for the frontend — Compose doesn't containerize it; see below).

### Steps

1. **Clone and enter the repo.**
   ```
   git clone <your-fork-or-repo-url>
   cd uni-project
   ```

2. **Create your environment file.** Copy the example and fill in real secrets:
   ```
   cp api/.env.example api/.env
   ```
   At minimum, replace `QR_SIGNING_SECRET` and `JWT_SECRET` with your own random strings (32+ characters — `python -c "import secrets; print(secrets.token_hex(32))"` works well) if you intend this to be anything other than a throwaway local instance. Leave `DEMO_MODE=true` for local testing (it enables one-click demo logins); set it to `false` before showing this to anyone who isn't you.

3. **Start the database, API, and face-service:**
   ```
   docker compose up --build
   ```
   First run will take a few minutes: `face-service`'s container installs `libgl1`/`libglib2.0-0` (OpenCV's system dependencies) and downloads the two ONNX face models (YuNet detector, SFace recognizer, ~10–15MB combined) from the OpenCV Zoo GitHub repo on first request — this happens automatically, no manual step needed, but it means the *very first* enroll/check-in call will be slower than the rest.

   Wait for `api` to log that it's serving on port 8000 and `face-service` on 8001. The `db` service has a healthcheck the other two wait on, so if `api` starts before Postgres is actually ready, Compose is already handling that — no race condition to work around.

4. **Run the frontend separately** (Compose doesn't containerize it in this repo):
   ```
   cd frontend
   npm install
   npm run dev
   ```
   This serves on `http://127.0.0.1:3000`. Use that exact origin, not `localhost:3000` — the API's CORS allow-list (`ALLOWED_ORIGINS` in `api/.env`) is matched exactly, and `127.0.0.1` vs `localhost` are different origins to a browser even though they resolve to the same place.

5. **Verify it's up:**
   - `curl http://localhost:8000/health` (or open it in a browser) should return a healthy JSON response.
   - `curl http://localhost:8001/health` likewise for face-service.
   - Open `http://127.0.0.1:3000` — you should see the SmartAttend login screen. With `DEMO_MODE=true`, there are one-click demo logins for admin/lecturer/student roles right on that screen.

### A gap to know about in this path
`docker-compose.yml` only mounts `database/001_initial.sql` into Postgres's auto-init directory. The later migrations (`002_attendance_attempts.sql` through `005_pending_students.sql`) are **not** applied automatically on a fresh Docker volume — you need to run them yourself once the `db` container is up:
```
docker compose exec -T db psql -U smart_attend -d smart_attend < database/002_attendance_attempts.sql
docker compose exec -T db psql -U smart_attend -d smart_attend < database/003_refresh_tokens.sql
docker compose exec -T db psql -U smart_attend -d smart_attend < database/004_class_schedules.sql
docker compose exec -T db psql -U smart_attend -d smart_attend < database/005_pending_students.sql
```
(Run these once, right after first startup, before using the app — features touching schedules, self-registration, or refresh-token revocation will fail with database errors otherwise.)

---

## Path B: Native (uv-based) — for development

This is the path actually used to build and test this project. It avoids Docker entirely, using SQLite as a dev-mode database fallback instead of Postgres.

### Prerequisites

- **Python 3.12 specifically** — not 3.13, not 3.14. This project hit a real, confirmed build failure on Python 3.14: `pydantic-core` (a dependency of both `api` and `face-service`) has no prebuilt wheel for 3.14, and building it from source requires a Rust toolchain and MSVC build tools most machines don't have. 3.12 has prebuilt wheels for every dependency this project uses and is what's pinned in `docker-compose.yml` too — stay on it.
- **[uv](https://docs.astral.sh/uv/)**, Astral's Python/venv manager. If you don't already have a Python 3.12 on PATH, uv can install one for you — this is the easiest way to get a clean, correctly-versioned interpreter without touching your system Python:
  ```
  # install uv itself (see https://docs.astral.sh/uv/getting-started/installation/ for your OS)
  uv python install 3.12
  ```
- **Node.js 18+** for the frontend.

Two separate Python services means **two separate virtual environments** — `api` and `face-service` have different, non-overlapping dependency sets (`opencv-python-headless` in particular is only needed by `face-service`), so don't try to share one venv between them.

### Steps

1. **Clone and enter the repo.**
   ```
   git clone <your-fork-or-repo-url>
   cd uni-project
   ```

2. **Set up the `api` service:**
   ```
   cd api
   uv venv --python 3.12
   uv pip install -r requirements.txt
   cp .env.example .env
   ```
   Edit `.env`:
   - For a pure local/no-Postgres setup, you can skip `DATABASE_URL` entirely if the codebase's SQLite fallback path is what you want to use — check `api/app/config.py` for the current default; otherwise point `DATABASE_URL` at a local Postgres instance you run yourself, in the same `postgresql+psycopg://user:pass@host:5432/dbname` shape as the example.
   - Set `QR_SIGNING_SECRET` and `JWT_SECRET` to real random values (see the `secrets.token_hex(32)` snippet above). The app refuses to start with the placeholder example values outside of an explicit local-dev exception — don't be surprised by a startup error here, it's intentional.
   - Set `FACE_SERVICE_URL=http://127.0.0.1:8001` (native services aren't on a Docker network, so use `127.0.0.1`, not the `face-service` hostname the Compose file uses).
   - Leave `ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000` unless you're serving the frontend from somewhere else.

3. **Set up `face-service`** (separate venv, separate terminal or `cd` back out first):
   ```
   cd ../face-service
   uv venv --python 3.12
   uv pip install -r requirements.txt
   ```
   `face-service` has no `.env` file of its own — its two tunable settings (`FACE_DISTANCE_THRESHOLD`, `FACE_MIN_FRAME_DIFFERENCE`) read from plain environment variables with working defaults (`1.128` and `6.0` respectively) if unset, so nothing else to configure here for a first run.

4. **Start both backend services** (two terminals):
   ```
   # terminal 1, from api/
   .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
   # (macOS/Linux: .venv/bin/python -m uvicorn app.main:app --reload --port 8000)

   # terminal 2, from face-service/
   .venv/Scripts/python.exe -m uvicorn main:app --reload --port 8001
   # (macOS/Linux: .venv/bin/python -m uvicorn main:app --reload --port 8001)
   ```
   On `face-service`'s first request that needs them, it downloads the YuNet and SFace ONNX model files from the OpenCV Zoo GitHub repo into `face-service/models/` (gitignored — they're fetched, not committed, same as the Docker path). This needs outbound internet access once; after that they're cached locally.

5. **Apply database migrations**, in order, against whatever database you pointed `DATABASE_URL` at (or, if you're on the SQLite dev fallback, this typically happens automatically via `Base.metadata.create_all()` on `api` startup for the base schema — check `api/app/main.py`'s startup logic, and apply the numbered `database/00N_*.sql` files by hand against Postgres if you're using it, in filename order: `001` → `005`).

6. **Start the frontend:**
   ```
   cd frontend
   npm install
   npm run dev
   ```
   Serves on `http://127.0.0.1:3000` (matches `frontend/package.json`'s `dev` script, which explicitly binds `--host 127.0.0.1` — again, use that exact origin for CORS to work).

7. **Verify:**
   - `http://localhost:8000/health` and `http://localhost:8001/health` both respond.
   - `http://127.0.0.1:3000` loads the login screen; demo logins work if `DEMO_MODE=true`.
   - Run the test suite to confirm the `api` install is sound:
     ```
     cd api
     .venv/Scripts/python.exe -m pytest -q
     ```
     Use `python -m pytest`, not `uv run pytest` or a bare `pytest` — on at least one Windows machine this project was developed on, a Windows "Application Control" policy blocked `pytest.exe`'s entrypoint specifically while allowing the same test run via `python -m pytest`. If your `pytest` invocation silently fails or gets blocked with no clear Python-level error, this is the first thing to try.

---

## Path C: Vercel (frontend) + Render (backend) — a real public URL

Vercel only serves static/frontend sites — it can't run the stateful `api` + `face-service` + Postgres trio this project needs. The frontend deploys to Vercel; the backend deploys to Render, which can run Docker containers and a managed Postgres database.

### 1. Deploy the frontend to Vercel
The repo root already has [vercel.json](vercel.json) telling Vercel to install and build from inside `frontend/` (Vercel's own root-level install otherwise finds nothing to install, since `package.json` at repo root has no dependencies — this is the fix for a `vite: command not found` build failure if you hit it). Connect the repo in Vercel as normal; no other config needed until step 3.

### 2. Deploy the backend to Render
The repo root has [render.yaml](render.yaml), a Render **Blueprint** that defines all three backend pieces in one file: a managed Postgres database (`smartattend-db`), the `api` service, and the `face-service` service, each built from its own `Dockerfile` (`api/Dockerfile`, `face-service/Dockerfile`).

1. In the Render dashboard: **New +** → **Blueprint** → connect this GitHub repo. Render reads `render.yaml` and proposes all three resources — confirm and deploy.
2. Wait for `smartattend-face-service` and `smartattend-api` to both show "Live." `smartattend-api` depends on `smartattend-face-service`'s public URL (set in `render.yaml` as `FACE_SERVICE_URL`) — if you rename the face-service in the Render dashboard, its public URL changes too, so update `FACE_SERVICE_URL` in `render.yaml` (or directly in the Render dashboard's environment tab for `smartattend-api`) to match.
3. `render.yaml` sets `ALLOWED_ORIGINS` to `https://uni-project-drab.vercel.app` — if your Vercel URL is different, update that value (in `render.yaml` or the Render dashboard) to your actual deployed frontend origin, exactly (protocol + host, no trailing slash), or every request from the frontend will fail CORS.
4. **Apply the database migrations** — Render's managed Postgres doesn't auto-run `database/001_initial.sql` the way the `pgvector/pgvector` Docker image does locally. From the Render Postgres dashboard's "Connect" tab, copy the **External Connection String**, then from a machine with `psql` installed:
   ```
   psql "<external-connection-string>" -f database/001_initial.sql
   psql "<external-connection-string>" -f database/002_attendance_attempts.sql
   psql "<external-connection-string>" -f database/003_refresh_tokens.sql
   psql "<external-connection-string>" -f database/004_class_schedules.sql
   psql "<external-connection-string>" -f database/005_pending_students.sql
   ```
   `001_initial.sql` includes `CREATE EXTENSION IF NOT EXISTS vector;` — Render Postgres supports pgvector natively, so this succeeds without any extra dashboard step. If it errors with a permissions issue, Render's docs say to contact `support@render.com` to have the extension enabled on that database first.

### 3. Connect the frontend to the backend
In the Vercel project's **Settings → Environment Variables**, add:
```
VITE_API_URL = https://smartattend-api.onrender.com
```
(use `smartattend-api`'s actual Render URL — check the Render dashboard if you renamed the service). Redeploy the frontend (Vercel → Deployments → Redeploy) so the new env var is baked into the build — Vite inlines `VITE_*` variables at build time, so just setting the variable without a redeploy has no effect.

### Two things worth knowing about this path
- **Render's free tier spins services down after inactivity** and takes tens of seconds to wake back up on the next request. `QR_TTL_SECONDS` defaults to 30 — a cold-started `api` can plausibly take longer than that to respond to the very first request after idle, which would show up as an expired/failed QR check-in on that first attempt. If you're demoing live, hit the site once a minute or two before you actually need it to "wake" the services first; a paid Render plan removes this entirely.
- `render.yaml` sets `DEMO_MODE=true` so the one-click demo logins (admin/lecturer/student) work out of the box — this is what answers "I don't have any credentials to log in with." Per [README.md](README.md) and [PRIVACY.md](PRIVACY.md), turn this off (`DEMO_MODE=false`, along with real rotated secrets) before this is ever shown to real students.

---

## Environment variables reference

All of these are read by `api` (from `api/.env`, or the container environment in Docker):

| Variable | Purpose | Notes |
|---|---|---|
| `DATABASE_URL` | Postgres connection string | `postgresql+psycopg://user:pass@host:5432/dbname`. Omit/adjust for a SQLite dev fallback if the codebase supports it in your version. |
| `QR_SIGNING_SECRET` | HMAC key signing the rotating check-in QR tokens | Must be changed from the placeholder before any real deployment — the app enforces this. |
| `QR_TTL_SECONDS` | How long each QR token stays valid | Default `30`. Shorter = harder to screenshot-and-share, less forgiving of slow scanning. |
| `FACE_DISTANCE_THRESHOLD` | Max embedding distance counted as a face match | Default `1.128`, SFace's own documented NORM_L2 threshold — don't change without understanding the recognition model's calibration. |
| `FACE_SERVICE_URL` | Where `api` reaches `face-service` | `http://face-service:8001` in Docker, `http://127.0.0.1:8001` natively. |
| `ALLOWED_ORIGINS` | CORS allow-list | Must exactly match the origin the frontend is actually served from, protocol and host included. |
| `JWT_SECRET` | Signs access/refresh tokens | Same "must change before real use" enforcement as `QR_SIGNING_SECRET`. |
| `DEMO_MODE` | Enables one-click demo logins on the login screen | `true` for local dev, **must be `false`** before this is shown to real users. |
| `TIMEZONE` | Used for scheduling/attendance-window calculations | Default `Africa/Lagos`. |

`face-service` reads two more, directly from the process environment (no `.env` file):

| Variable | Purpose | Default |
|---|---|---|
| `FACE_DISTANCE_THRESHOLD` | Same meaning as above, duplicated here since face-service does its own match comparison | `1.128` |
| `FACE_MIN_FRAME_DIFFERENCE` | Minimum pixel difference required between the two liveness-check frames | `6.0` — this is a starting value, not independently tuned against real usage; raise it if replay/static-photo attempts are getting through, lower it if genuine live check-ins are being rejected as "not live." |
| `FACE_MODEL_DIR` | Where the downloaded ONNX models are cached | `models` (relative to `face-service/`) |

---

## Troubleshooting

Issues actually hit while building this project, in case you hit the same ones:

- **"No Python found" / wrong Python version picked up.** Confirm `uv python list` shows a 3.12 install, and that you ran `uv venv --python 3.12` (not a bare `uv venv`, which may pick whatever's on PATH). A stray Python 3.13/3.14 install on PATH is the most common cause of dependency install failures here.
- **`pydantic-core` build failure / asks for a Rust compiler.** You're on the wrong Python version — see above. This isn't a flaky wheel-hosting issue, it's version 3.14 genuinely lacking a prebuilt wheel at the time this was built.
- **`face-service` fails to import `cv2` / OpenCV errors about missing shared libraries (`libGL.so.1` etc.), Docker path only.** This is why the Compose file installs `libgl1`/`libglib2.0-0` before `pip install` — `opencv-python-headless` still needs a couple of system graphics libraries despite the "headless" name. If you're running face-service outside Docker on a minimal Linux distro (not Windows/macOS), you may need to install those two packages yourself.
- **`uv run pytest` does nothing / gets silently blocked (Windows only).** A Windows "Application Control" policy can block `pytest.exe`'s entrypoint specifically. Use `.venv/Scripts/python.exe -m pytest` instead — routes around the same block by invoking pytest as a module rather than an executable.
- **Frontend requests fail with CORS errors in the browser console.** Almost always an origin mismatch — check that the URL you're loading the frontend from (`http://127.0.0.1:3000` vs `http://localhost:3000`) exactly matches an entry in `ALLOWED_ORIGINS`. They are different origins to a browser even though they point at the same machine.
- **First enroll/check-in request is very slow, then fast after that.** Expected — `face-service` downloads its two ONNX model files from GitHub on first use and caches them locally. Make sure the machine has outbound internet access for that first call; after that, it's fully local.
- **Self-registration/scheduling endpoints error out on a fresh Docker Compose setup.** You likely haven't applied the `002`–`005` migration files — see the callout in the Docker Compose section above; only `001_initial.sql` runs automatically.
- **A previously-enrolled account's face check always fails after pulling a newer version of this repo.** If the face-verification pipeline changed (embedding model, embedding dimensions), old enrollments are invalidated by design — the stored biometric template doesn't match what the new pipeline computes for the same face. Re-enroll the affected account.

---

## What's not covered here

This guide gets the system running for development or a demo. It does **not** cover production hardening (real secrets, HTTPS/TLS termination, a real reverse proxy, backup strategy for the database, or institutional sign-off on handling biometric data) — see `README.md`'s "before deploying anywhere real" checklist and [PRIVACY.md](PRIVACY.md) for what still needs deciding before this touches real students.
