import { useState, type FormEvent, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/auth/AuthContext";
import { ApiError } from "@/shared/api/client";

/**
 * Email+password only for now. Google/Facebook/LinkedIn OAuth are live
 * on the backend (Baseline stage, apps/api/auth.py) but need a
 * client-side redirect flow (window.location to
 * /v1/auth/{provider}/login, then landing back with a token) that isn't
 * wired up yet -- flagged here rather than silently left out.
 */
export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const platformAdmin = await login(email, password);
      navigate(platformAdmin ? "/platform" : "/app/workspaces");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: "var(--color-surface-raised)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          padding: "32px",
          width: "320px",
        }}
      >
        <h1 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "24px" }}>
          Sign in to AutonomousIQ
        </h1>

        <label style={{ display: "block", marginBottom: "12px" }}>
          <span style={{ display: "block", fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "4px" }}>
            Email
          </span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={inputStyle}
          />
        </label>

        <label style={{ display: "block", marginBottom: "16px" }}>
          <span style={{ display: "block", fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "4px" }}>
            Password
          </span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={inputStyle}
          />
        </label>

        {error && (
          <p style={{ color: "var(--color-negative)", fontSize: "13px", marginBottom: "12px" }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          style={{
            width: "100%",
            padding: "10px",
            background: "var(--color-accent)",
            color: "#ffffff",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontWeight: 600,
            cursor: submitting ? "default" : "pointer",
            opacity: submitting ? 0.7 : 1,
          }}
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

const inputStyle: CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
  color: "var(--color-text)",
  fontSize: "14px",
};
