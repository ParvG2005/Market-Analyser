import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Panel } from "../components/common/Panel";
import { useAuthStore } from "../stores/authStore";

/** Supabase-backed sign-in. On success, navigates to the app home. */
export function Login() {
  const signIn = useAuthStore((s) => s.signIn);
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signIn(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="brand-mark" aria-hidden="true">
            M
          </div>
          <div className="brand-name">Market Assistant</div>
        </div>

        <Panel title="Sign in">
          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="auth-field" htmlFor="login-email">
              <span className="auth-label">Email</span>
              <input
                id="login-email"
                className="auth-input"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="auth-field" htmlFor="login-password">
              <span className="auth-label">Password</span>
              <input
                id="login-password"
                className="auth-input"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            {error !== null && <p className="auth-error" role="alert">{error}</p>}

            <button type="submit" className="auth-submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </Panel>

        <p className="auth-alt">
          Need an account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}
