import { useState, type FormEvent, type CSSProperties } from "react";
import { apiRequest, ApiError } from "@/shared/api/client";

export function RequestAccessPage() {
  const [companyName, setCompanyName] = useState("");
  const [contactInfo, setContactInfo] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiRequest("/v1/tenant-requests", {
        method: "POST",
        body: { company_name: companyName, contact_info: contactInfo },
      });
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div style={{ maxWidth: "480px", margin: "0 auto", padding: "96px 32px", textAlign: "center" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "12px" }}>Request received</h1>
        <p style={{ color: "var(--color-text-muted)" }}>
          An AutonomousIQ Admin will review your request and reach out to set up your tenant.
        </p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "420px", margin: "0 auto", padding: "80px 32px" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "8px" }}>Request access</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "24px" }}>
        No self-serve signup yet (FR-1) -- a human reviews every request.
      </p>

      <form onSubmit={handleSubmit}>
        <label style={{ display: "block", marginBottom: "12px" }}>
          <span style={{ display: "block", fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "4px" }}>
            Company name
          </span>
          <input
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
            style={inputStyle}
          />
        </label>

        <label style={{ display: "block", marginBottom: "16px" }}>
          <span style={{ display: "block", fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "4px" }}>
            Contact email
          </span>
          <input
            type="email"
            value={contactInfo}
            onChange={(e) => setContactInfo(e.target.value)}
            required
            style={inputStyle}
          />
        </label>

        {error && <p style={{ color: "var(--color-negative)", fontSize: "13px", marginBottom: "12px" }}>{error}</p>}

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
          }}
        >
          {submitting ? "Submitting…" : "Submit request"}
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
