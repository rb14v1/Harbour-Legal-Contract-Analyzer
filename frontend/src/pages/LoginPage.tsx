import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("reviewer@legalcontracts.demo");
  const [password, setPassword] = useState("DemoPass123!");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/contracts");
    } catch {
      setError("Login failed. Check your email and password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Legal Contract Analyzer</h1>
        <p className="auth-subtitle">Sign in to review and query contracts.</p>
        {error && <div className="error-banner">{error}</div>}
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </label>
        <label>
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in..." : "Sign in"}
        </button>
        <div className="demo-hint">
          <strong>Demo logins</strong>
          <div>reviewer@legalcontracts.demo / DemoPass123!</div>
          <div>admin@legalcontracts.demo / DemoPass123!</div>
        </div>
      </form>
    </div>
  );
}
