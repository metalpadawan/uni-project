import { useState } from "react";
import { Camera, Check } from "lucide-react";
import { useFaceCapture } from "./useFaceCapture";
import { api } from "./api";

export default function StudentRegister({ onDone }) {
  const [consent, setConsent] = useState(false);
  const { videoRef, captured, message, capturing, capture } = useFaceCapture(consent);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [submitted, setSubmitted] = useState(false);
  const photoReady = captured.length === 1;

  async function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api.registerStudent({
        name: f.get("name").trim(),
        email: f.get("email").trim(),
        password: f.get("password"),
        matric_no: f.get("matric_no").trim(),
        department: f.get("department").trim(),
        level: Number(f.get("level")),
        photo: captured[0],
        biometric_consent: consent,
      });
      setSubmitted(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (submitted)
    return (
      <div className="success">
        <span>
          <Check />
        </span>
        <h2>Registration submitted</h2>
        <p>
          An admin will review your details and face template. You'll be able
          to sign in once your account is approved.
        </p>
        <button className="primary" onClick={onDone}>
          Back to sign in
        </button>
      </div>
    );

  return (
    <form className="student-form" onSubmit={submit} style={{ textAlign: "left" }}>
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
        Password
        <input
          name="password"
          type="password"
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
        I consent to storing a biometric face template for attendance
        verification.
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
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <button
        className="primary"
        disabled={busy || !consent || !photoReady}
        style={{ gridColumn: "1 / -1" }}
      >
        {busy
          ? "Submitting…"
          : consent && !photoReady
            ? "Capture a photo first"
            : "Submit for review"}
      </button>
    </form>
  );
}
