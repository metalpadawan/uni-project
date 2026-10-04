import { useState } from "react";
import { Check } from "lucide-react";
import { api } from "./api";

export default function EnrollStudent() {
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
      const created = await api.enrollStudent({
        name: f.get("name").trim(),
        email: f.get("email").trim(),
        temporary_password: f.get("password"),
        matric_no: f.get("matric_no").trim(),
        department: f.get("department").trim(),
        level: Number(f.get("level")),
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
    <div className="panel" style={{ padding: 24, marginTop: 20 }}>
      <h3>Enrol a student</h3>
      <p style={{ color: "var(--muted)", fontSize: 12, margin: "6px 0 18px" }}>
        Creates the student's sign-in immediately. Face enrolment is not
        required for account creation.
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
        <button
          className="primary"
          disabled={busy}
          style={{ gridColumn: "1 / -1" }}
        >
          {busy ? "Enrolling…" : "Enrol student"}
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
          {success.name} ({success.matric_no}) can now sign in.
        </p>
      )}
    </div>
  );
}
