import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <div style={{ maxWidth: "880px", margin: "0 auto", padding: "96px 32px 64px" }}>
      <h1 style={{ fontSize: "40px", fontWeight: 700, lineHeight: 1.2, marginBottom: "16px" }}>
        Your data, ledgered, gated, and explainable.
      </h1>
      <p style={{ fontSize: "18px", color: "var(--color-text-muted)", marginBottom: "32px", maxWidth: "640px" }}>
        AutonomousIQ connects your live databases and documents to an AI planner that proposes queries,
        Tracker edits, and charts -- and never runs anything without a human approving it first.
      </p>
      <div style={{ display: "flex", gap: "12px" }}>
        <Link
          to="/request-access"
          style={{
            textDecoration: "none",
            background: "var(--color-accent)",
            color: "#ffffff",
            fontWeight: 600,
            padding: "12px 24px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          Request access
        </Link>
        <Link
          to="/product"
          style={{
            textDecoration: "none",
            border: "1px solid var(--color-border)",
            color: "var(--color-text)",
            fontWeight: 600,
            padding: "12px 24px",
            borderRadius: "var(--radius-sm)",
          }}
        >
          See how it works
        </Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "24px", marginTop: "64px" }}>
        {[
          { title: "Live-editable Trackers", body: "Spreadsheet-grade formulas, backed by a real dependency graph and recalc engine -- not a static export." },
          { title: "Approval-gated AI", body: "Every AI-proposed query, edit, or chart sits in a queue until someone with the right grant signs off." },
          { title: "One planner, many sources", body: "Connect Postgres, MySQL, SQL Server, or Snowflake, and search your uploaded documents from one chat." },
        ].map((card) => (
          <div
            key={card.title}
            style={{
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "20px",
            }}
          >
            <h3 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "8px" }}>{card.title}</h3>
            <p style={{ fontSize: "13px", color: "var(--color-text-muted)", margin: 0 }}>{card.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
