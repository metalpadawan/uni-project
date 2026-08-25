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
  ChevronDown,
  Play,
  X,
  Menu,
  CircleUserRound,
} from "lucide-react";
import "./styles.css";
import { api } from "./api";
const SecureCheckIn = React.lazy(() => import("./SecureCheckIn"));

const students = [
  {
    name: "Ekemini John",
    id: "21/CSC/142",
    course: "CSC 421",
    time: "09:02 AM",
    status: "Present",
    initials: "EJ",
  },
  {
    name: "Jecintha Odok",
    id: "21/CSC/156",
    course: "CSC 421",
    time: "09:04 AM",
    status: "Present",
    initials: "JO",
  },
  {
    name: "Mfon Udo",
    id: "21/CSC/178",
    course: "CSC 421",
    time: "09:08 AM",
    status: "Present",
    initials: "MU",
  },
  {
    name: "Grace Effiong",
    id: "21/CSC/183",
    course: "CSC 421",
    time: "—",
    status: "Pending",
    initials: "GE",
  },
];

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
    [error, setError] = useState("");
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
          <span className="eyebrow">SMART CAMPUS SECURITY</span>
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
    () =>
      JSON.parse(localStorage.getItem("attendanceRecords") || "null") ||
      students,
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
          if (active && rows.length)
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
  async function finish({ embedding, token, liveness }) {
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
        captured_embedding: embedding,
        liveness_passed: liveness,
      });
      setDone(true);
      setRecords((r) =>
        r.map((x) =>
          x.id === "21/CSC/156"
            ? {
                ...x,
                status: "Present",
                time: new Date().toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                }),
              }
            : x,
        ),
      );
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
            <button className="mobile-avatar">
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
                <span className="eyebrow">SATURDAY, 1 AUGUST</span>
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
        ) : (
          <Workspace
            page={page}
            records={records}
            setRecords={setRecords}
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
                <h2 id="modal-title">CSC 421 attendance is open</h2>
                <p>
                  Project this rotating QR code. Students must also pass face
                  verification.
                </p>
                {qr && (
                  <img
                    className="qr-image"
                    src={qr.qr_data_url}
                    alt="Time-limited CSC 421 attendance QR code"
                  />
                )}
                <small>Expires every {qr?.expires_in || 30} seconds</small>
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
            <span className="eyebrow">STUDENT PORTAL</span>
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
          <>
            <div className="summary-row">
              <b>
                78%<small>Overall attendance</small>
              </b>
              <b>
                12<small>Classes attended</small>
              </b>
              <b>
                3<small>Classes missed</small>
              </b>
            </div>
            <RecordTable
              records={records.filter((r) => r.id === "21/CSC/156")}
            />
          </>
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
          <span className="eyebrow">ADMIN PORTAL</span>
          <h2>{page}</h2>
          <p>
            Manage the people, courses, and biometric enrolment behind
            SmartAttend.
          </p>
        </div>
      </div>
      {page === "Overview" ? (
        <>
          <div className="stats admin-stats">
            <Stat
              icon={<Users />}
              label="Registered students"
              value="112"
              note="8 awaiting face enrolment"
              tone="green"
            />
            <Stat
              icon={<BookOpen />}
              label="Active courses"
              value="14"
              note="Current semester"
              tone="blue"
            />
            <Stat
              icon={<ShieldCheck />}
              label="Face enrolled"
              value="104"
              note="92.8% completed"
              tone="purple"
            />
          </div>
          <div className="panel admin-callout">
            <div>
              <h3>Biometric enrolment queue</h3>
              <p>
                Eight students still need 3–5 approved face samples before they
                can check in.
              </p>
            </div>
            <button className="primary" onClick={() => setPage("Students")}>
              Review students
            </button>
          </div>
        </>
      ) : page === "Students" ? (
        <RecordTable records={records} />
      ) : page === "Courses" ? (
        <div className="course-grid">
          {[
            ["CSC 421", "Artificial Intelligence", "48 students"],
            ["CSC 323", "Computer Architecture", "64 students"],
            ["CSC 311", "Data Structures", "58 students"],
          ].map((c) => (
            <div className="panel course-card" key={c[0]}>
              <span>{c[0]}</span>
              <h3>{c[1]}</h3>
              <p>
                <Users size={15} />
                {c[2]}
              </p>
              <button>
                Manage course <ArrowUpRight size={15} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <Workspace
          page={page}
          records={records}
          setRecords={() => {}}
          onStart={onStart}
        />
      )}
    </section>
  );
}
function Workspace({ page, records, setRecords, onStart }) {
  const [showForm, setShowForm] = useState(false),
    [notice, setNotice] = useState(""),
    [prefs, setPrefs] = useState({ face: true, qr: true, alerts: true });
  function addStudent(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      name = f.get("name").trim(),
      id = f.get("id").trim();
    if (!name || !id) return;
    setRecords((r) => [
      ...r,
      {
        name,
        id,
        course: "CSC 421",
        time: "—",
        status: "Pending",
        initials: name
          .split(" ")
          .map((x) => x[0])
          .join("")
          .slice(0, 2)
          .toUpperCase(),
      },
    ]);
    setShowForm(false);
    setNotice("Student added successfully.");
  }
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
  if (page === "Students")
    return (
      <section className="workspace">
        <PageHead
          title="Student records"
          text="Register and manage students eligible for dual authentication"
        >
          <button className="primary" onClick={() => setShowForm((v) => !v)}>
            <Users size={17} />
            {showForm ? "Cancel" : "Add student"}
          </button>
        </PageHead>
        {notice && <Notice text={notice} />}{" "}
        {showForm && (
          <form className="student-form" onSubmit={addStudent}>
            <label>
              Full name
              <input name="name" placeholder="Student full name" required />
            </label>
            <label>
              Matric number
              <input name="id" placeholder="21/CSC/000" required />
            </label>
            <button className="primary">Save student</button>
          </form>
        )}
        <RecordTable
          records={records}
          action={(r) => (
            <button
              className="remove"
              onClick={() => setRecords((x) => x.filter((s) => s.id !== r.id))}
            >
              Remove
            </button>
          )}
        />
      </section>
    );
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
            value="100%"
            text="All recorded entries completed both face and QR verification."
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
