# SmartAttend

Multi-authentication attendance platform for the University of Cross River State. The build follows `Smart_Attendance_System_Build_Guide.md`: attendance is recorded only when face verification and a short-lived session QR both pass.

## Current milestone

- Monorepo foundation: `frontend`, `api`, and `database`.
- PostgreSQL/pgvector schema and Docker Compose environment.
- FastAPI session creation and 30-second signed QR rotation.
- Atomic `POST /attendance/checkin` double-lock contract.
- Duplicate attendance protection and clear expired-QR/face-failure errors.
- Security unit tests for QR signing, tampering, and expiry.

The current face input is a measured distance plus liveness result. Camera capture and the dedicated face service are the next milestone; the API already enforces the documented `< 0.6` threshold.

## Run API locally

```powershell
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Use `http://127.0.0.1:8000/docs` for the interactive API.

## Run frontend

```powershell
cd frontend
npm install
npm run dev
```

