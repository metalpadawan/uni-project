import { useState } from "react";
import { Camera, Check } from "lucide-react";
import { useFaceCapture } from "./useFaceCapture";
import { api } from "./api";

export default function EnrollStudent() {
  const [consent, setConsent] = useState(false);
  const { videoRef, captured, message, capturing, capture } = useFaceCapture(consent);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [success, setSuccess] = useState(null);
  const photoReady = captured.length === 1;

  async function submit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setBusy(true);
    setError("");
    setSuccess(null);
    try {
      const created = await api.enrollStudent({
        name: f.get("name").trim(),
        email: f.get("email").trim(),
        temporary_password: f.get("password"),
        matric_no: f.get("matric_no").trim(),
        department: f.get("department").trim(),
        level: Number(f.get("level")),
        photo: captured[0],
        biometric_consent: consent,
      });
      setSuccess(created);
      form.reset();
      setConsent(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel" style={{ padding: 24, marginTop: 20 }}>
      <h3>Enrol a student</h3>
      <p style={{ color: "var(--muted)", fontSize: 12, margin: "6px 0 18px" }}>
        Creates the student's sign-in and captures the face template used for
        check-in. The student should be at the camera for this step.
      </p>
      <form className="student-form" onSubmit={submit}>
        <label>
          Full name
          <input name="name" placeholder="Jane Student" minLength={2} required />
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
          Matric number
          <input name="matric_no" placeholder="21/CSC/000" minLength={5} required />
        </label>
        <label>
          Department
          <input name="department" defaultValue="Computer Science" required />
        </label>
        <label>
          Level
          <input
            name="level"
            type="number"
            defaultValue={400}
            min={100}
            max={900}
            step={100}
            required
          />
        </label>
        <label
          style={{
            gridColumn: "1 / -1",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 400,
          }}
        >
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            style={{ width: "auto", height: "auto" }}
          />
          The student has given explicit consent to store a biometric face
          template.
        </label>
        {consent && (
          <div style={{ gridColumn: "1 / -1" }}>
            <div className="camera-frame" style={{ maxWidth: 360 }}>
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                aria-label="Face capture preview"
              />
              <div className="face-guide" />
            </div>
            <p className="capture-message" role="status">
              {message}
            </p>
            {!photoReady && (
              <button
                type="button"
                className="outline"
                disabled={capturing}
                onClick={capture}
              >
                {capturing ? "Capturing…" : "Capture photo"} <Camera size={15} />
              </button>
            )}
          </div>
        )}
        <button
          className="primary"
          disabled={busy || !consent || !photoReady}
          style={{ gridColumn: "1 / -1" }}
        >
          {busy
            ? "Enrolling…"
            : consent && !photoReady
              ? "Capture a photo first"
              : "Enrol student"}
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
          {success.name} ({success.matric_no}) enrolled with a face template.
        </p>
      )}
    </div>
  );
}
