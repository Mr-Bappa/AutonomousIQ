const SECTIONS = [
  { title: "Trackers", body: "Grids with real formulas -- SUM, IF, VLOOKUP-style lookups, and more -- computed by a dependency-graph recalc engine, not a client-side spreadsheet library pretending to be one." },
  { title: "Chat + Planner", body: "Ask a question in plain language. The planner classifies intent, decides which tool to use -- SQL, Tracker lookup, document search, or chart -- and either answers directly (document search) or proposes an action for approval." },
  { title: "Approvals", body: "Every proposed SQL query, Tracker write, or chart sits in a queue. Only someone holding an approver grant on the right workspace (or a tenant Admin) can let it through." },
  { title: "Ingestion", body: "Connect Postgres, MySQL, SQL Server, or Snowflake as a live source, or upload documents directly. Everything feeds the same planner." },
  { title: "Team & access", body: "Admins manage teams and roles tenant-wide; Developers can invite within their own team. Access to resources is granted per-workspace, not all-or-nothing." },
];

export function ProductPage() {
  return (
    <div style={{ maxWidth: "780px", margin: "0 auto", padding: "64px 32px" }}>
      <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>How AutonomousIQ works</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "40px" }}>
        A quick tour of what's inside, once you're signed in.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
        {SECTIONS.map((s) => (
          <div key={s.title}>
            <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "6px", color: "var(--color-accent-strong)" }}>
              {s.title}
            </h3>
            <p style={{ fontSize: "14px", color: "var(--color-text-muted)", margin: 0 }}>{s.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
