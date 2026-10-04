# SmartAttend 1,000-user capacity plan

This repository now supports a horizontally scaled deployment. It is not truthful to claim that the current free Render deployment can serve 1,000 simultaneous users: free Render web services cannot scale beyond one instance, and face verification is CPU-intensive.

## Target

- A burst of 1,000 students can sign in without being rejected merely because they share a campus public IP address.
- Attendance check-ins remain available while lecturers and administrators use the service.
- A failed instance does not stop the whole service.

This is a capacity target, not a substitute for a load test. Run the test in section 4 before an assessment or real rollout.

## 1. Required Render configuration

Use a paid Render workspace. Keep all resources in the same region.

| Resource | Starting configuration | Why |
| --- | --- | --- |
| API | `1c-2g`, 3 instances, `API_WORKERS=2` | Spreads login and normal API traffic across six Python processes. |
| Face service | `2c-4g`, 4 instances, `FACE_SERVICE_WORKERS=2` | Face matching is CPU-bound; this provides eight isolated inference processes. |
| PostgreSQL | Paid plan with at least 2 CPU / 4 GB and PgBouncer enabled | Prevents a burst of API workers from exhausting direct database connections. |
| Render Key Value | `1g`, private access only | Provides a shared Redis-compatible counter for rate limits across API instances. |

In Render, create **New > Key Value**, call it `smartattend-rate-limit`, select the same region, and set its public IP allow-list to empty (the API reaches it privately). Copy its **internal connection URL**.

In **smartattend-api > Environment**, add:

```text
RATE_LIMIT_STORAGE_URI=<the internal redis:// URL>
LOGIN_RATE_LIMIT=1500/minute
CHECKIN_RATE_LIMIT=2000/minute
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
DATABASE_POOL_TIMEOUT_SECONDS=10
DATABASE_POOL_RECYCLE_SECONDS=1800
API_WORKERS=2
```

In **smartattend-face-service > Environment**, add:

```text
FACE_SERVICE_WORKERS=2
```

Then, in each service's **Compute** page, set the instance counts above. For a Pro workspace, use autoscaling instead: API minimum 3 / maximum 6; face service minimum 4 / maximum 8; CPU target 60%.

Finally, enable the database **Connection Pool** (PgBouncer), then change the API's `DATABASE_URL` to the database's internal *connection-pool* URL (port 6432) and choose **Save and deploy**. Do this during a maintenance window because enabling the pool restarts the database.

## 2. Why these settings are necessary

- Browser sign-in requests may arrive from one university NAT address. The old five-requests-per-minute IP limit would reject almost every student. The new configurable burst limits allow the scheduled sign-in/check-in surge while a shared Key Value store keeps the limit consistent across API instances.
- Each API worker has a bounded SQLAlchemy pool. PgBouncer safely multiplexes those short database transactions rather than requiring one Postgres connection for every request.
- OpenCV's detector has mutable state. The face service now serializes inference inside each worker, then gains throughput by using independent workers and instances rather than unsafe concurrent access to one detector.

## 3. Deployment order

1. Commit and push this change.
2. Create and configure Render Key Value, database pooling, worker counts, and instances as described above.
3. Confirm `https://<api>/health/ready` returns `{"status":"ok","database":"ready"}`.
4. Warm every API and face-service instance before the attendance period. Do not use free plans for this target.
5. Keep the Vercel frontend on its stable production domain and retain the exact domain in `ALLOWED_ORIGINS`.

## 4. Required load test

Test a staging deployment, never the live class database. Use 1,000 real-looking test accounts and ramp traffic gradually, for example 100 new users every 15 seconds. Record:

- login success rate: at least 99.5%;
- API 95th-percentile response time: below 2 seconds after warm-up;
- check-in completion rate: at least 99%;
- no database connection saturation or API/face-service out-of-memory restart;
- no `429` responses for valid students during the planned burst.

Do not attempt 1,000 face check-ins in the same 15-second QR window until the staged test proves the face-service sizing. If that test misses the target, first increase face-service instances; do not weaken the face or QR checks.

## 5. Monitoring and rollback

Create uptime checks for `/health/ready` and the face service's `/health`. Alert on sustained 5xx responses, database pool waiting connections, or CPU above 80%. Keep the previous Render deployment available; if the load test exposes a regression, roll back the API and face service together.
