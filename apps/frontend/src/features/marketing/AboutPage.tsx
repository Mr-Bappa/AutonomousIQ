export function AboutPage() {
  return (
    <div style={{ maxWidth: "680px", margin: "0 auto", padding: "64px 32px" }}>
      <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "16px" }}>About</h1>
      <p style={{ color: "var(--color-text-muted)", lineHeight: 1.7 }}>
        AutonomousIQ is being built stage by stage -- Business Case, PRD, Architecture, Standards,
        and now Layer-wise Development -- with every decision logged and every approval-gated
        action kept genuinely gated, not just described as gated. This site and the product behind
        it are a Phase 0 build: functional, deliberately simple in places, and flagged everywhere
        it's cutting a corner rather than hiding it.
      </p>
    </div>
  );
}
