# SmartAttend Release Checklist

Use this as the final handoff guide. Steps marked **You** require your accounts, device access, or institutional approval; the source-code work is already in the repository.

## 1. Save and verify the work

1. **You:** Review the changed files in your editor. Do not add the existing `.claude/` directory unless you know it belongs in the repository.
2. **You:** Run `git status`, then commit the project changes (including `.github/workflows/ci.yml`, `.env.example`, and this checklist):
   ```powershell
   git add README.md SETUP.md RELEASE_CHECKLIST.md .env.example .github api database docker-compose.yml face-service frontend render.yaml
   git commit -m "Complete attendance workflow and deployment hardening"
   git push
   ```
3. **You:** Open the **Actions** tab in GitHub and wait for the `CI` workflow to pass. It builds the frontend and runs the API and face-service tests on Python 3.12.

## 2. Run it locally with Docker Desktop

1. **You:** Install and start Docker Desktop. Docker was not available on this computer during the final verification.
2. **You:** From the repository root, create local Compose settings:
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
3. **You:** Replace the three password/secret placeholders with different private values. For a throwaway demo only, set `DEMO_MODE=true`; leave it `false` for every real deployment.
4. **You:** Start the backend services:
   ```powershell
   docker compose up --build
   ```
5. **You:** In a second terminal, start the frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
6. **You:** Open `http://127.0.0.1:5173`, then confirm both `http://localhost:8000/health` and `http://localhost:8001/health` return healthy JSON.

### Phone QR testing on the same Wi-Fi

1. **You:** Run `ipconfig` and copy the laptop's **IPv4 Address** for the Wi-Fi adapter, for example `192.168.1.25`.
2. **You:** In the root `.env`, append your laptop Wi-Fi URL (for example, `http://192.168.1.25:5173`) to `ALLOWED_ORIGINS`.
3. **You:** Create `frontend/.env.local` with `VITE_API_URL=http://192.168.1.25:8000`, then restart Docker Compose and Vite. Allow Windows Firewall access on private networks if asked.
4. **You:** Sign in as the student, select the open class, and use the in-app QR scanner after live face capture. The QR contains a short-lived signed token, not a website link; both checks are required before attendance is recorded.

## 3. Configure first real users

1. **You:** With `DEMO_MODE=false`, bootstrap the first administrator once using the `POST /auth/bootstrap` endpoint in the API docs at `http://localhost:8000/docs` (or your deployed API `/docs`).
2. **You:** Sign in as that administrator and approve student registrations, create lecturer accounts, create courses, and assign each course's lecturer.
3. **You:** Open each course and add enrolled students by matriculation number using the new enrolment manager.
4. **You:** Sign in as a lecturer, create a schedule/session, display its QR code, and test a student check-in. Face-and-QR attendance still requires the student to have a stored face template.

## 4. Deploy for your assessment/demo

1. **You:** Create a Render account and select **New + → Blueprint**, then choose this GitHub repository. Render reads `render.yaml` and creates the database, API, and face service.
2. **You:** In each Render service's environment settings, set different strong values for `JWT_SECRET`, `QR_SIGNING_SECRET`, and `POSTGRES_PASSWORD`; retain `DEMO_MODE=false`.
3. **You:** Connect to the Render PostgreSQL database and enable pgvector once:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   The numbered migrations in `database/` must all be applied to an existing production database before the new API version is released.
4. **You:** Create a Vercel project from the same repository, choosing `frontend` as its root directory. Add `VITE_API_URL` with the public Render API URL (for example, `https://smartattend-api.onrender.com`) and deploy.
5. **You:** Add the final Vercel URL to the API's `ALLOWED_ORIGINS` value in Render, redeploy the API, and test login from the public frontend. The exact origin matters.
6. **You:** Bootstrap the production administrator through `/docs`, then repeat the user/course/schedule setup in section 3.
7. **You:** If you need to retain successful attendance photos, upgrade the API to a paid Render plan, attach a 1 GB disk at `/var/data`, set `ATTENDANCE_CAPTURE_DIR=/var/data/attendance-captures`, and redeploy. The API must remain a single instance while it uses this local disk.

## 5. Acceptance test before submission

1. Log in, refresh the browser, and confirm the session remains active.
2. Register a student and approve the account as an administrator.
3. Enrol the approved student in a course and verify a lecturer can view their course roster.
4. Create a live attendance session and ensure its QR code expires when configured to do so.
5. Attempt check-in with an unrecognised face: it must be rejected and logged as an attempt.
6. Check in with the enrolled student’s face and valid QR: it must create exactly one attendance record.
7. Repeat the successful check-in: it must not create a duplicate record.
8. Log out and confirm the browser can no longer use the old session.

## 6. Windows restriction on this machine

This computer’s Application Control policy blocks standard Python DLLs such as `pyexpat` and `unicodedata`. That is why complete local pytest reruns cannot finish here; it is an operating-system policy, not an application test failure. Ask your system administrator to allow the approved Python 3.12 installation and its standard-library DLLs, or rely on the included GitHub Actions run for independent verification.
