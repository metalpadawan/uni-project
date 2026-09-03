import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ScanFace,
  QrCode,
  ShieldCheck,
  LayoutDashboard,
  Users,
  CalendarDays,
  FileBarChart,
  Settings,
  Bell,
  Search,
  ArrowUpRight,
  Check,
  Clock3,
  BookOpen,
  Play,
  X,
  Menu,
  CircleUserRound,
  UserPlus,
} from "lucide-react";
import "./styles.css";
import { api } from "./api";
const SecureCheckIn = React.lazy(() => import("./SecureCheckIn"));
const EnrollStudent = React.lazy(() => import("./EnrollStudent"));
const StudentRegister = React.lazy(() => import("./StudentRegister"));

const titleRole = (role) =>
  role ? role[0].toUpperCase() + role.slice(1) : "Student";
const homeFor = (role) =>
  role === "Lecturer"
    ? "Dashboard"
    : role === "Student"
      ? "Check in"
      : "Overview";

function LoginScreen({ onLogin, demoMode }) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [mode, setMode] = useState("login");
  async function submit(e) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      onLogin(await api.login(data.get("email"), data.get("password")));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  async function demo(role) {
    setBusy(true);
    setError("");
    try {
      onLogin(await api.demoLogin(role));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-brand">
        <Logo />
        <div>
          <h1>Attendance that proves presence.</h1>
          <p>
            Face recognition and a short-lived classroom QR code work together
            to stop proxy attendance.
          </p>
          <div className="login-feature">
            <ScanFace />
            <span>
              <b>Face verification</b>
              <small>Confirms student identity</small>
            </span>
          </div>
          <div className="login-feature">
            <QrCode />
            <span>
              <b>Dynamic QR code</b>
              <small>Confirms classroom presence</small>
            </span>
          </div>
        </div>
      </section>
      <section className="login-panel">
        {mode === "register" ? (
          <div>
            <span className="login-lock">
              <ShieldCheck />
            </span>
            <h2>Student registration</h2>
            <p>
              Submit your details and a face capture. An admin reviews every
              request before your account can sign in.
            </p>
            <React.Suspense fallback={<p>Loading…</p>}>
              <StudentRegister onDone={() => setMode("login")} />
            </React.Suspense>
            <button
              type="button"
              className="outline full"
              style={{ marginTop: 14 }}
              onClick={() => setMode("login")}
            >
              Back to sign in
            </button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <span className="login-lock">
              <ShieldCheck />
            </span>
            <h2>Welcome back</h2>
            <p>Sign in with your university account.</p>
            <label htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="name@unicross.edu.ng"
              required
            />
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              minLength="8"
              placeholder="Enter your password"
              required
            />
            {error && (
              <div className="login-error" role="alert">
                {error}
              </div>
            )}
            <button className="primary full" disabled={busy}>
              {busy ? "Signing in…" : "Sign in securely"}
            </button>
            <button
              type="button"
              className="outline full"
              style={{ marginTop: 10 }}
              onClick={() => setMode("register")}
            >
              New student? Register here
            </button>
            {demoMode && (
              <div className="demo-access">
                <span>Local development access</span>
                <div>
                  {["Student", "Lecturer", "Admin"].map((role) => (
                    <button
                      type="button"
                      disabled={busy}
                      key={role}
                      onClick={() => demo(role)}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <small className="privacy-copy">
              Biometric data is protected and used only for attendance
              verification.
            </small>
          </form>
        )}
      </section>
    </main>
  );
}

function Logo() {
  return (
    <div className="logo">
      <span>
        <ScanFace size={23} />
      </span>
      <div>
        Smart<span>Attend</span>
        <small>UNICROSS</small>
      </div>
    </div>
  );
}
const NOW_SERVING_SEGMENTS = 12;
function NowServing({ qr }) {
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    if (!qr?.expires_at) return;
    const tick = () =>
      setRemaining(
        Math.max(0, Math.round((new Date(qr.expires_at) - Date.now()) / 1000)),
      );
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [qr?.expires_at]);

  const total = qr?.expires_in || 30;
  const lit = Math.round((remaining / total) * NOW_SERVING_SEGMENTS);

  return (
    <div className="now-serving">
      <p className="now-serving-label">Now serving · rotates automatically</p>
      <div className="now-serving-clock">
        {String(remaining).padStart(2, "0")}
        <small> sec</small>
      </div>
      <div className="now-serving-track" aria-hidden="true">
        {Array.from({ length: NOW_SERVING_SEGMENTS }).map((_, i) => (
          <i key={i} className={i < lit ? "chase" : ""} />
        ))}
      </div>
    </div>
  );
}
function App() {
  const savedUser = JSON.parse(
    sessionStorage.getItem("smartattend_user") || "null",
  );
  const [user, setUser] = useState(savedUser);
  const [role, setRole] = useState(
    savedUser ? titleRole(savedUser.role) : "Lecturer",
  );
  const [page, setPage] = useState(
    savedUser ? homeFor(titleRole(savedUser.role)) : "Dashboard",
  );
  const [menu, setMenu] = useState(false);
  const [modal, setModal] = useState(null);
  const [step, setStep] = useState(1);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [session, setSession] = useState(null);
  const [qr, setQr] = useState(null);
  const [openSessions, setOpenSessions] = useState([]);
  const [sessionsBusy, setSessionsBusy] = useState(false);
  const [records, setRecords] = useState(
    () => JSON.parse(localStorage.getItem("attendanceRecords") || "null") || [],
  );
  const demoMode = import.meta.env.VITE_DEMO_MODE !== "false";
  useEffect(
    () => localStorage.setItem("attendanceRecords", JSON.stringify(records)),
    [records],
  );
  useEffect(() => {
    if (!user || role !== "Student") return;
    let active = true;
    setSessionsBusy(true);
    api
      .openSessions()
      .then((rows) => {
        if (active) setOpenSessions(rows);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setSessionsBusy(false);
      });
    return () => {
      active = false;
    };
  }, [user, role, page]);
  useEffect(() => {
    if (!user || role !== "Lecturer" || page !== "Dashboard" || modal) return;
    let active = true;
    api
      .currentSession()
      .then((current) => {
        if (active && current) setSession(current);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [user, role, page]);
  useEffect(() => {
    if (modal !== "lecturer-session" || !session?.session_id) return;
    let active = true;
    const refresh = () =>
      api
        .rotateQr(session.session_id)
        .then((value) => {
          if (active) setQr(value);
        })
        .catch((value) => {
          if (active) setError(value.message);
        });
    const attendance = () =>
      api
        .sessionAttendance(session.session_id)
        .then((rows) => {
          if (active)
            setRecords(
              rows.map((row) => ({
                ...row,
                course: session.course_code,
                time: new Date(row.time).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
                status: row.status === "present" ? "Present" : "Flagged",
                initials: row.name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")
                  .slice(0, 2),
              })),
            );
        })
        .catch(() => {});
    const qrTimer = window.setInterval(refresh, 20000);
    const attendanceTimer = window.setInterval(attendance, 3000);
    refresh();
    attendance();
    return () => {
      active = false;
      clearInterval(qrTimer);
      clearInterval(attendanceTimer);
    };
  }, [modal, session?.session_id]);
  const stats = useMemo(
    () => ({
      present: records.filter((r) => r.status === "Present").length,
      total: 48,
    }),
    [records],
  );
  const nav =
    role === "Lecturer"
      ? [
          ["Dashboard", LayoutDashboard],
          ["Schedule", BookOpen],
          ["Students", Users],
          ["Attendance", CalendarDays],
          ["Reports", FileBarChart],
          ["Settings", Settings],
        ]
      : role === "Student"
        ? [
            ["Check in", ScanFace],
            ["My attendance", CalendarDays],
            ["Profile", CircleUserRound],
          ]
        : [
            ["Overview", LayoutDashboard],
            ["Accounts", UserPlus],
            ["Students", Users],
            ["Courses", BookOpen],
            ["Reports", FileBarChart],
            ["Settings", Settings],
          ];
  async function changeRole(next) {
    setBusy(true);
    setError("");
    try {
      const loggedIn = await api.demoLogin(next);
      setUser(loggedIn);
      setRole(next);
      setPage(homeFor(next));
      setMenu(false);
    } catch (e) {
      setError(e.message);
      setModal("api-error");
    } finally {
      setBusy(false);
    }
  }
  async function startSession() {
    setBusy(true);
    setError("");
    try {
      const created = await api.createSession();
      const freshQr = await api.rotateQr(created.session_id);
      setSession(created);
      setQr(freshQr);
      setModal("lecturer-session");
    } catch (e) {
      setError(e.message);
      setModal("api-error");
    } finally {
      setBusy(false);
    }
  }
  async function endSession() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      await api.closeSession(session.session_id);
      close();
      setSession(null);
      setQr(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function finish({ frameA, frameB, token }) {
    if (!session) {
      setError("Choose an open attendance session first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.checkIn({
        session_id: session.session_id,
        qr_token: token,
        frame_a: frameA,
        frame_b: frameB,
      });
      setDone(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function beginStudentCheckIn(selected) {
    setSession(selected);
    setQr(null);
    setStep(1);
    setDone(false);
    setError("");
    setModal("checkin");
  }
  function close() {
    setModal(null);
    setStep(1);
    setDone(false);
    setError("");
  }
  if (!user)
    return (
      <LoginScreen
        onLogin={(loggedIn) => {
          const next = titleRole(loggedIn.role);
          setUser(loggedIn);
          setRole(next);
          setPage(homeFor(next));
        }}
        demoMode={demoMode}
      />
    );
  return (
    <div className="app">
      <aside className={menu ? "open" : ""}>
        <div className="aside-top">
          <Logo />
          <button
            className="close"
            onClick={() => setMenu(false)}
            aria-label="Close menu"
          >
            <X />
          </button>
        </div>
        {demoMode && (
          <div className="role-switch" aria-label="Development portal switcher">
            {["Student", "Lecturer", "Admin"].map((r) => (
              <button
                key={r}
                className={role === r ? "selected" : ""}
                onClick={() => changeRole(r)}
              >
                {r}
              </button>
            ))}
          </div>
        )}
        <span className="nav-label">{role} portal</span>
        <nav>
          {nav.map(([n, I]) => (
            <button
              key={n}
              className={page === n ? "active" : ""}
              onClick={() => {
                setPage(n);
                setMenu(false);
              }}
            >
              <I size={19} />
              {n}
            </button>
          ))}
        </nav>
        <div className="support">
          <ShieldCheck />
          <b>Secure & reliable</b>
          <p>Dual authentication keeps every attendance record protected.</p>
        </div>
        <div className="profile">
          <div className="avatar">
            {user.name
              .split(" ")
              .map((x) => x[0])
              .join("")
              .slice(0, 2)}
          </div>
          <div>
            <b>{user.name}</b>
            <span>{role}</span>
          </div>
          <button
            className="logout"
            onClick={() => {
              api.logout();
              setUser(null);
            }}
          >
            Log out
          </button>
        </div>
      </aside>
      <main>
        <header>
          <button
            className="hamb"
            onClick={() => setMenu(true)}
            aria-label="Open menu"
          >
            <Menu />
          </button>
          <div>
            <p>Department of Computer Science · {role} Portal</p>
            <h1>{page}</h1>
          </div>
          <div className="header-actions">
            <label>
              <Search size={17} />
              <input aria-label="Search" placeholder="Search records..." />
            </label>
            <button className="icon" aria-label="Notifications">
              <Bell size={19} />
              <i />
            </button>
            <button
              className="mobile-avatar"
              onClick={() => setMenu(true)}
              aria-label="Open account menu"
            >
              <CircleUserRound />
            </button>
          </div>
        </header>
        {role !== "Lecturer" ? (
          <PortalView
            role={role}
            page={page}
            records={records}
            setPage={setPage}
            sessions={openSessions}
            sessionsBusy={sessionsBusy}
            onStart={beginStudentCheckIn}
          />
        ) : page === "Dashboard" ? (
          <>
            <section className="welcome">
              <div>
                <h2>Good afternoon, Dr. Umoh.</h2>
                <p>Here’s what’s happening with your classes today.</p>
              </div>
              <button
                className="primary"
                disabled={busy}
                onClick={startSession}
              >
                <Play size={17} fill="currentColor" />
                {busy ? "Starting…" : "Start attendance"}
              </button>
            </section>
            {session && modal !== "lecturer-session" && (
              <section className="admin-callout" style={{ margin: "0 38px 22px" }}>
                <div>
                  <h3>{session.course_code} attendance is live</h3>
                  <p>A scheduled or previously started session is open right now.</p>
                </div>
                <button className="primary" onClick={() => setModal("lecturer-session")}>
                  <QrCode size={16} /> Show live QR
                </button>
              </section>
            )}
            <section className="stats">
              <Stat
                icon={<CalendarDays />}
                label="Today's sessions"
                value="3"
                note="2 completed"
                tone="purple"
              />
              <Stat
                icon={<Users />}
                label="Students present"
                value="86"
                suffix="/ 112"
                note="76.8% attendance"
                tone="green"
              />
              <Stat
                icon={<ScanFace />}
                label="Face verified"
                value="84"
                note="97.7% success rate"
                tone="blue"
              />
              <Stat
                icon={<QrCode />}
                label="QR verified"
                value="86"
                note="100% success rate"
                tone="orange"
              />
            </section>
            <section className="grid">
              <div className="panel attendance">
                <div className="panel-head">
                  <div>
                    <h3>Live attendance</h3>
                    <p>CSC 421 · Artificial Intelligence</p>
                  </div>
                  <span className="live">
                    <i />
                    LIVE
                  </span>
                </div>
                <div className="session-progress">
                  <div>
                    <b>
                      {stats.present} of {stats.total} students
                    </b>
                    <span>Session closes at 10:30 AM</span>
                  </div>
                  <strong>
                    {Math.round((stats.present / stats.total) * 100)}%
                  </strong>
                </div>
                <div className="bar">
                  <i
                    style={{ width: `${(stats.present / stats.total) * 100}%` }}
                  />
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Matric no.</th>
                        <th>Time</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.map((r) => (
                        <tr key={r.id}>
                          <td>
                            <span className="student-avatar">{r.initials}</span>
                            <b>{r.name}</b>
                          </td>
                          <td>{r.id}</td>
                          <td>{r.time}</td>
                          <td>
                            <span
                              className={"status " + r.status.toLowerCase()}
                            >
                              {r.status === "Present" ? (
                                <Check size={13} />
                              ) : (
                                <Clock3 size={13} />
                              )}{" "}
                              {r.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button className="view" onClick={() => setPage("Attendance")}>
                  View attendance register <ArrowUpRight size={16} />
                </button>
              </div>
              <div className="sidecol">
                <div className="panel next">
                  <div className="panel-head">
                    <div>
                      <h3>Next session</h3>
                      <p>Today’s schedule</p>
                    </div>
                    <button aria-label="Session options">•••</button>
                  </div>
                  <span className="time-badge">11:00 AM</span>
                  <h4>CSC 323</h4>
                  <b>Computer Architecture</b>
                  <p>
                    <Clock3 size={15} /> 11:00 AM – 1:00 PM
                  </p>
                  <p>
                    <Users size={15} /> 64 enrolled students
                  </p>
                  <button className="outline" onClick={startSession}>
                    <Play size={16} /> Prepare session
                  </button>
                </div>
                <div className="panel method">
                  <h3>Dual authentication</h3>
                  <p>Every student is verified through two secure layers.</p>
                  <div>
                    <span>
                      <ScanFace />
                    </span>
                    <b>
                      Face recognition<small>Identity confirmed</small>
                    </b>
                    <Check />
                  </div>
                  <i></i>
                  <div>
                    <span>
                      <QrCode />
                    </span>
                    <b>
                      Dynamic QR code<small>Presence confirmed</small>
                    </b>
                    <Check />
                  </div>
                </div>
              </div>
            </section>
          </>
        ) : page === "Schedule" ? (
          <LecturerSchedule />
        ) : (
          <Workspace
            page={page}
            records={records}
            onStart={() => setModal("checkin")}
          />
        )}
        <footer>
          Smart Attendance System · Department of Computer Science · University
          of Cross River State
        </footer>
      </main>
      {menu && (
        <button
          className="scrim"
          onClick={() => setMenu(false)}
          aria-label="Close navigation"
        />
      )}
      {modal && (
        <div className="modal-back" role="presentation">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <button className="modal-x" onClick={close} aria-label="Close">
              <X />
            </button>
            {modal === "api-error" ? (
              <div className="success error-state">
                <span>
                  <X />
                </span>
                <h2 id="modal-title">Service unavailable</h2>
                <p>{error}</p>
                <button className="primary" onClick={close}>
                  Close
                </button>
              </div>
            ) : modal === "lecturer-session" ? (
              <div className="session-modal">
                <span className="live">
                  <i />
                  LIVE SESSION
                </span>
                <h2 id="modal-title">
                  {session?.course_code || "Class"} attendance is open
                </h2>
                <p>
                  Project this rotating QR code. Students must also pass face
                  verification.
                </p>
                {qr && (
                  <div className="ticket-frame">
                    <img
                      className="qr-image"
                      src={qr.qr_data_url}
                      alt={`Time-limited ${session?.course_code || "class"} attendance QR code`}
                    />
                  </div>
                )}
                <NowServing qr={qr} />
                <button
                  className="primary full"
                  onClick={async () => {
                    setBusy(true);
                    try {
                      setQr(await api.rotateQr(session.session_id));
                    } catch (e) {
                      setError(e.message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  {busy ? "Refreshing…" : "Refresh QR now"}
                </button>
                <button
                  className="outline full"
                  disabled={busy}
                  onClick={endSession}
                >
                  Close attendance session
                </button>
              </div>
            ) : modal === "checkin" && !done ? (
              <React.Suspense
                fallback={
                  <div className="face-frame" role="status">
                    Loading secure camera…
                  </div>
                }
              >
                <SecureCheckIn
                  course={session}
                  busy={busy}
                  error={error}
                  onComplete={finish}
                />
              </React.Suspense>
            ) : done ? (
              <div className="success">
                <span>
                  <Check />
                </span>
                <h2 id="modal-title">Attendance verified</h2>
                <p>
                  Face identity and QR session code matched successfully. The
                  record has been saved.
                </p>
                <button className="primary" onClick={close}>
                  Back to dashboard
                </button>
              </div>
            ) : (
              <>
                <span className="modal-icon">
                  {step === 1 ? <ScanFace /> : <QrCode />}
                </span>
                <small>STEP {step} OF 2</small>
                <h2 id="modal-title">
                  {step === 1
                    ? "Verify student identity"
                    : "Confirm classroom presence"}
                </h2>
                <p>
                  {step === 1
                    ? "Camera landmark extraction is the next module; the server still performs the authoritative face comparison."
                    : "The current lecturer session QR will be submitted securely to the API."}
                </p>
                {step === 1 ? (
                  <div className="face-frame">
                    <ScanFace size={70} />
                    <span>Development embedding ready</span>
                  </div>
                ) : (
                  <div className="code-entry">
                    <label>Active session</label>
                    <input
                      readOnly
                      value={
                        session
                          ? "CSC 421 · QR ready"
                          : "No active lecturer session"
                      }
                    />
                    <small>QR tokens expire after 30 seconds</small>
                  </div>
                )}
                {error && (
                  <p className="inline-error" role="alert">
                    {error}
                  </p>
                )}
                <button
                  className="primary full"
                  disabled={busy}
                  onClick={() => (step === 1 ? setStep(2) : finish())}
                >
                  {busy
                    ? "Verifying…"
                    : step === 1
                      ? "Continue to QR check"
                      : "Verify both & mark present"}
                  <ArrowUpRight size={17} />
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
function Stat({ icon, label, value, suffix, note, tone }) {
  return (
    <div className="stat">
      <span className={tone}>{icon}</span>
      <div>
        <p>{label}</p>
        <h3>
          {value}
          <small>{suffix}</small>
        </h3>
        <b>{note}</b>
      </div>
    </div>
  );
}
function PortalView({
  role,
  page,
  records,
  setPage,
  onStart,
  sessions = [],
  sessionsBusy = false,
}) {
  if (role === "Student")
    return (
      <section className="portal-page">
        <div className="portal-hero student-hero">
          <div>
            <h2>{page === "Check in" ? "Mark attendance securely" : page}</h2>
            <p>
              {page === "Check in"
                ? "Choose an open class, verify your face, then scan its rotating QR code."
                : "Track your verified attendance and course eligibility."}
            </p>
          </div>
          <div className="double-lock">
            <div>
              <ScanFace />
              <b>1. Verify face</b>
              <small>Live identity match</small>
            </div>
            <span>+</span>
            <div>
              <QrCode />
              <b>2. Scan QR</b>
              <small>Classroom presence</small>
            </div>
          </div>
        </div>
        {page === "My attendance" ? (
          <StudentAttendanceHistory />
        ) : page === "Profile" ? (
          <div className="panel profile-card">
            <div className="avatar large">JO</div>
            <h3>Jecintha Odok</h3>
            <p>21/CSC/156 · Computer Science</p>
            <span className="status present">
              <ShieldCheck size={14} /> Face enrolled
            </span>
          </div>
        ) : (
          <>
            <div className="workspace-head">
              <div>
                <h2>Open attendance sessions</h2>
                <p>Only courses you are enrolled in appear here.</p>
              </div>
            </div>
            {sessionsBusy ? (
              <div className="panel empty-session" role="status">
                Loading open classes…
              </div>
            ) : sessions.length ? (
              <div className="course-grid">
                {sessions.map((item) => (
                  <article className="panel course-card" key={item.session_id}>
                    <span>{item.course_code}</span>
                    <h3>{item.course_title}</h3>
                    <p>
                      <Clock3 size={15} />
                      Closes{" "}
                      {new Date(item.ends_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                    <button className="primary" onClick={() => onStart(item)}>
                      <ScanFace size={17} />
                      Start secure check-in
                    </button>
                  </article>
                ))}
              </div>
            ) : (
              <div className="panel empty-session">
                <QrCode />
                <h3>No open sessions</h3>
                <p>
                  When your lecturer starts attendance, the course will appear
                  here automatically.
                </p>
              </div>
            )}
            <div className="trust-note">
              <ShieldCheck />
              <div>
                <b>Your attendance needs both checks</b>
                <p>
                  A face match alone or QR scan alone can never mark you
                  present.
                </p>
              </div>
            </div>
          </>
        )}
      </section>
    );
  return (
    <section className="portal-page">
      <div className="workspace-head">
        <div>
          <h2>{page}</h2>
          <p>
            Manage the people, courses, and biometric enrolment behind
            SmartAttend.
          </p>
        </div>
      </div>
      {page === "Overview" ? (
        <AdminOverview setPage={setPage} />
      ) : page === "Accounts" ? (
        <>
          <PendingApprovals />
          <CreateAccount />
          <React.Suspense
            fallback={
              <div className="panel" style={{ padding: 24, marginTop: 20 }}>
                Loading face enrolment…
              </div>
            }
          >
            <EnrollStudent />
          </React.Suspense>
        </>
      ) : page === "Students" ? (
        <AdminStudents />
      ) : page === "Courses" ? (
        <AdminCourses />
      ) : (
        <Workspace page={page} records={records} onStart={onStart} />
      )}
    </section>
  );
}
function StudentAttendanceHistory() {
  const [history, setHistory] = useState(null),
    [error, setError] = useState("");

  useEffect(() => {
    api.myAttendance().then(setHistory).catch((e) => setError(e.message));
  }, []);

  if (error)
    return (
      <p className="inline-error" role="alert">
        {error}
      </p>
    );
  if (!history)
    return <div className="panel empty-session">Loading your attendance…</div>;

  const present = history.filter((r) => r.status === "present").length;
  const missed = history.filter((r) => r.status !== "present").length;
  const rate = history.length ? Math.round((present / history.length) * 100) : 0;

  return (
    <>
      <div className="summary-row">
        <b>
          {rate}%<small>Overall attendance</small>
        </b>
        <b>
          {present}
          <small>Classes attended</small>
        </b>
        <b>
          {missed}
          <small>Classes missed</small>
        </b>
      </div>
      {!history.length ? (
        <div className="panel empty-session">
          <ScanFace />
          <h3>No attendance yet</h3>
          <p>Check in to a class and it'll show up here.</p>
        </div>
      ) : (
        <div className="records panel">
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((r, i) => (
                <tr key={i}>
                  <td>
                    <b>{r.course_code}</b> — {r.course_title}
                  </td>
                  <td>
                    {new Date(r.time).toLocaleString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      month: "short",
                      day: "numeric",
                    })}
                  </td>
                  <td>
                    <span className={"status " + (r.status === "present" ? "present" : "pending")}>
                      {r.status === "present" ? <Check size={13} /> : <Clock3 size={13} />}{" "}
                      {r.status === "present" ? "Present" : "Flagged"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
function AdminOverview({ setPage }) {
  const [overview, setOverview] = useState(null),
    [error, setError] = useState("");

  useEffect(() => {
    api.adminOverview().then(setOverview).catch((e) => setError(e.message));
  }, []);

  if (error)
    return (
      <p className="inline-error" role="alert">
        {error}
      </p>
    );
  if (!overview) return <div className="panel empty-session">Loading overview…</div>;

  return (
    <>
      <div className="stats admin-stats">
        <Stat
          icon={<Users />}
          label="Registered students"
          value={String(overview.registered_students)}
          note="All approved accounts"
          tone="green"
        />
        <Stat
          icon={<BookOpen />}
          label="Active courses"
          value={String(overview.active_courses)}
          note="Current semester"
          tone="blue"
        />
        <Stat
          icon={<ShieldCheck />}
          label="Pending registrations"
          value={String(overview.pending_registrations)}
          note="Awaiting admin review"
          tone="purple"
        />
      </div>
      {overview.pending_registrations > 0 && (
        <div className="panel admin-callout">
          <div>
            <h3>Registrations waiting for review</h3>
            <p>
              {overview.pending_registrations} student
              {overview.pending_registrations === 1 ? "" : "s"} submitted a
              registration that needs your approval or rejection.
            </p>
          </div>
          <button className="primary" onClick={() => setPage("Accounts")}>
            Review requests
          </button>
        </div>
      )}
    </>
  );
}
function AdminStudents() {
  const [students, setStudents] = useState([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");

  useEffect(() => {
    api
      .listStudents()
      .then(setStudents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error)
    return (
      <p className="inline-error" role="alert">
        {error}
      </p>
    );
  if (loading) return <div className="panel empty-session">Loading students…</div>;
  if (!students.length)
    return (
      <div className="panel empty-session">
        <Users />
        <h3>No students yet</h3>
        <p>Enrol a student or approve a pending registration to see them here.</p>
      </div>
    );

  return (
    <div className="records panel">
      <table>
        <thead>
          <tr>
            <th>Student</th>
            <th>Matric number</th>
            <th>Department</th>
            <th>Level</th>
          </tr>
        </thead>
        <tbody>
          {students.map((s) => (
            <tr key={s.id}>
              <td>
                <b>{s.name}</b>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>{s.email}</div>
              </td>
              <td>{s.matric_no}</td>
              <td>{s.department}</td>
              <td>{s.level}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function AdminCourses() {
  const [courses, setCourses] = useState([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");

  useEffect(() => {
    api
      .listCourses()
      .then(setCourses)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error)
    return (
      <p className="inline-error" role="alert">
        {error}
      </p>
    );
  if (loading) return <div className="panel empty-session">Loading courses…</div>;
  if (!courses.length)
    return (
      <div className="panel empty-session">
        <BookOpen />
        <h3>No courses yet</h3>
        <p>Courses appear here once a lecturer starts a session or sets up a schedule.</p>
      </div>
    );

  return (
    <div className="course-grid">
      {courses.map((c) => (
        <div className="panel course-card" key={c.id}>
          <span>{c.code}</span>
          <h3>{c.title}</h3>
        </div>
      ))}
    </div>
  );
}
function PendingApprovals() {
  const [pending, setPending] = useState([]),
    [loading, setLoading] = useState(true),
    [busyId, setBusyId] = useState(null),
    [error, setError] = useState("");

  function refresh() {
    setLoading(true);
    return api
      .pendingStudents()
      .then(setPending)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function approve(id) {
    setBusyId(id);
    setError("");
    try {
      await api.approveStudent(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function reject(id) {
    setBusyId(id);
    setError("");
    try {
      await api.rejectStudent(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  if (loading)
    return (
      <div className="panel" style={{ padding: 24 }}>
        Loading pending registrations…
      </div>
    );
  if (!pending.length) return null;

  return (
    <div className="panel" style={{ padding: 24 }}>
      <h3>Pending student registrations</h3>
      <p style={{ color: "var(--muted)", fontSize: 12, margin: "6px 0 18px" }}>
        Students who registered themselves. Review and approve or reject each
        request.
      </p>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <div className="records panel" style={{ boxShadow: "none" }}>
        <table>
          <thead>
            <tr>
              <th>Student</th>
              <th>Matric number</th>
              <th>Department</th>
              <th>Level</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pending.map((request) => (
              <tr key={request.id}>
                <td>
                  <b>{request.name}</b>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    {request.email}
                  </div>
                </td>
                <td>{request.matric_no}</td>
                <td>{request.department}</td>
                <td>{request.level}</td>
                <td style={{ display: "flex", gap: 8 }}>
                  <button
                    className="primary"
                    disabled={busyId === request.id}
                    onClick={() => approve(request.id)}
                  >
                    Approve
                  </button>
                  <button
                    className="remove"
                    disabled={busyId === request.id}
                    onClick={() => reject(request.id)}
                  >
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
function CreateAccount() {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(null);
  async function submit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setBusy(true);
    setError("");
    setSuccess(null);
    try {
      const created = await api.register({
        name: f.get("name").trim(),
        email: f.get("email").trim(),
        password: f.get("password"),
        role: f.get("role"),
      });
      setSuccess(created);
      form.reset();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="panel" style={{ padding: 24 }}>
      <h3>Create a lecturer or admin account</h3>
      <p style={{ color: "var(--muted)", fontSize: 12, margin: "6px 0 18px" }}>
        This creates a private sign-in the account owner can use on the login
        screen right away. Share the temporary password with them through a
        secure channel.
      </p>
      <form className="student-form" onSubmit={submit}>
        <label>
          Full name
          <input name="name" placeholder="Dr. Jane Doe" minLength={2} required />
        </label>
        <label>
          Email address
          <input
            name="email"
            type="email"
            placeholder="name@unicross.edu.ng"
            required
          />
        </label>
        <label>
          Temporary password
          <input
            name="password"
            type="text"
            placeholder="At least 8 characters"
            minLength={8}
            required
          />
        </label>
        <label>
          Role
          <select name="role" defaultValue="lecturer">
            <option value="lecturer">Lecturer</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className="notice" role="status">
          <Check size={15} />
          {success.name} can now sign in as {success.email}.
        </p>
      )}
      <small style={{ display: "block", color: "var(--muted)", marginTop: 14 }}>
        Student accounts need biometric enrolment and aren’t created from this
        form yet.
      </small>
    </div>
  );
}
const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function LecturerSchedule() {
  const [schedule, setSchedule] = useState([]),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");

  function refresh() {
    setLoading(true);
    return api
      .listSchedule()
      .then(setSchedule)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api.addSchedule({
        course_code: f.get("course_code").trim(),
        course_title: f.get("course_title").trim(),
        day_of_week: Number(f.get("day_of_week")),
        start_time: f.get("start_time"),
        duration_minutes: Number(f.get("duration_minutes")),
      });
      e.currentTarget.reset();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id) {
    setBusy(true);
    setError("");
    try {
      await api.deleteSchedule(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="workspace">
      <PageHead
        title="Weekly class schedule"
        text="Attendance opens and closes on its own at these times — no need to click Start."
      />
      <form className="student-form" onSubmit={submit}>
        <label>
          Course code
          <input name="course_code" placeholder="CSC 421" required />
        </label>
        <label>
          Course title
          <input name="course_title" placeholder="Artificial Intelligence" required />
        </label>
        <label>
          Day
          <select name="day_of_week" defaultValue="0">
            {DAY_NAMES.map((day, index) => (
              <option key={day} value={index}>
                {day}
              </option>
            ))}
          </select>
        </label>
        <label>
          Start time
          <input name="start_time" type="time" defaultValue="09:00" required />
        </label>
        <label>
          Duration (minutes)
          <input
            name="duration_minutes"
            type="number"
            defaultValue={120}
            min={5}
            max={360}
            required
          />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Saving…" : "Add to schedule"}
        </button>
      </form>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <div className="panel empty-session">Loading schedule…</div>
      ) : schedule.length ? (
        <div className="records panel">
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>Day</th>
                <th>Start time</th>
                <th>Duration</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {schedule.map((entry) => (
                <tr key={entry.id}>
                  <td>
                    <b>{entry.course_code}</b> — {entry.course_title}
                  </td>
                  <td>{DAY_NAMES[entry.day_of_week]}</td>
                  <td>{entry.start_time}</td>
                  <td>{entry.duration_minutes} min</td>
                  <td>
                    <button
                      className="remove"
                      disabled={busy}
                      onClick={() => remove(entry.id)}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="panel empty-session">
          <BookOpen />
          <h3>No scheduled classes yet</h3>
          <p>Add a course above and it'll open attendance automatically every week.</p>
        </div>
      )}
    </section>
  );
}
function LecturerRoster() {
  const [roster, setRoster] = useState([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");

  useEffect(() => {
    api
      .roster()
      .then(setRoster)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error)
    return (
      <p className="inline-error" role="alert">
        {error}
      </p>
    );
  if (loading)
    return (
      <section className="workspace">
        <div className="panel empty-session">Loading your students…</div>
      </section>
    );

  return (
    <section className="workspace">
      <PageHead
        title="Enrolled students"
        text="Students enrolled in the courses you teach."
      />
      {!roster.length ? (
        <div className="panel empty-session">
          <Users />
          <h3>No enrolled students yet</h3>
          <p>Students will appear here once they're enrolled in one of your courses.</p>
        </div>
      ) : (
        roster.map((course) => (
          <div className="records panel" style={{ marginBottom: 16 }} key={course.course_code}>
            <div className="panel-head" style={{ padding: "16px 20px 0" }}>
              <div>
                <h3>{course.course_code}</h3>
                <p>{course.course_title}</p>
              </div>
            </div>
            {course.students.length ? (
              <table>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Matric number</th>
                    <th>Department</th>
                    <th>Level</th>
                  </tr>
                </thead>
                <tbody>
                  {course.students.map((s) => (
                    <tr key={s.matric_no}>
                      <td>{s.name}</td>
                      <td>{s.matric_no}</td>
                      <td>{s.department}</td>
                      <td>{s.level}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ padding: "0 20px 16px", color: "var(--muted)", fontSize: 12 }}>
                No students enrolled in this course yet.
              </p>
            )}
          </div>
        ))
      )}
    </section>
  );
}
function Workspace({ page, records, onStart }) {
  const [notice, setNotice] = useState(""),
    [prefs, setPrefs] = useState({ face: true, qr: true, alerts: true });
  function exportCsv() {
    const csv = [
      "Student,Matric Number,Course,Time,Status",
      ...records.map((r) =>
        [r.name, r.id, r.course, r.time, r.status].join(","),
      ),
    ].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "CSC-421-attendance.csv";
    a.click();
    URL.revokeObjectURL(a.href);
    setNotice("Attendance report downloaded.");
  }
  if (page === "Students") return <LecturerRoster />;
  if (page === "Attendance")
    return (
      <section className="workspace">
        <PageHead
          title="Attendance register"
          text="CSC 421 · Artificial Intelligence · Today"
        >
          <button className="primary" onClick={onStart}>
            <ScanFace size={17} />
            Verify student
          </button>
        </PageHead>
        <div className="summary-row">
          <b>
            {records.filter((r) => r.status === "Present").length}
            <small>Present</small>
          </b>
          <b>
            {records.filter((r) => r.status === "Pending").length}
            <small>Pending</small>
          </b>
          <b>
            {records.length}
            <small>Enrolled</small>
          </b>
        </div>
        <RecordTable records={records} />
      </section>
    );
  if (page === "Reports")
    return (
      <section className="workspace">
        <PageHead
          title="Attendance reports"
          text="Review and export verified attendance data."
        >
          <button className="primary" onClick={exportCsv}>
            <FileBarChart size={17} />
            Export CSV
          </button>
        </PageHead>
        {notice && <Notice text={notice} />}
        <div className="report-grid">
          <Report
            title="Current attendance rate"
            value={`${Math.round((records.filter((r) => r.status === "Present").length / records.length) * 100) || 0}%`}
            text={`${records.filter((r) => r.status === "Present").length} of ${records.length} enrolled students verified`}
          />
          <Report
            title="Authentication integrity"
            value={`${Math.round((records.filter((r) => r.status === "Present").length / (records.filter((r) => r.status === "Present" || r.status === "Flagged").length || 1)) * 100)}%`}
            text={
              records.some((r) => r.status === "Flagged")
                ? `${records.filter((r) => r.status === "Flagged").length} attempt(s) failed a face or QR check and were flagged for review.`
                : "All recorded entries completed both face and QR verification."
            }
          />
        </div>
      </section>
    );
  return (
    <section className="workspace">
      <PageHead
        title="System settings"
        text="Configure authentication requirements for attendance sessions."
      />
      <div className="settings panel">
        {[
          ["face", "Require face recognition"],
          ["qr", "Require dynamic QR code"],
          ["alerts", "Attendance alerts"],
        ].map(([k, t]) => (
          <label key={k}>
            <span>
              <b>{t}</b>
              <small>
                {k === "face"
                  ? "Verify registered facial identity."
                  : k === "qr"
                    ? "Confirm classroom presence."
                    : "Show session notifications."}
              </small>
            </span>
            <input
              type="checkbox"
              checked={prefs[k]}
              onChange={() => setPrefs((p) => ({ ...p, [k]: !p[k] }))}
            />
            <i />
          </label>
        ))}
        <button
          className="primary"
          onClick={() => setNotice("Settings saved on this device.")}
        >
          Save settings
        </button>
        {notice && <Notice text={notice} />}
      </div>
    </section>
  );
}
function PageHead({ title, text, children }) {
  return (
    <div className="workspace-head">
      <div>
        <h2>{title}</h2>
        <p>{text}</p>
      </div>
      {children}
    </div>
  );
}
function Notice({ text }) {
  return (
    <div className="notice">
      <Check size={16} />
      {text}
    </div>
  );
}
function RecordTable({ records, action }) {
  return (
    <div className="records panel">
      <table>
        <thead>
          <tr>
            <th>Student</th>
            <th>Matric number</th>
            <th>Time</th>
            <th>Face + QR status</th>
            {action && <th />}
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.id}>
              <td>
                <span className="student-avatar">{r.initials}</span>
                <b>{r.name}</b>
              </td>
              <td>{r.id}</td>
              <td>{r.time}</td>
              <td>
                <span className={"status " + r.status.toLowerCase()}>
                  {r.status === "Present" ? (
                    <ShieldCheck size={13} />
                  ) : (
                    <Clock3 size={13} />
                  )}{" "}
                  {r.status}
                </span>
              </td>
              {action && <td>{action(r)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Report({ title, value, text }) {
  return (
    <div className="panel report-card">
      <span>{title}</span>
      <strong>{value}</strong>
      <p>{text}</p>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
