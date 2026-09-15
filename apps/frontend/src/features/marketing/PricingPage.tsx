const TIERS = [
  { name: "Starter", price: "Contact us", features: ["1 workspace", "Up to 5 users", "Document search"] },
  { name: "Team", price: "Contact us", features: ["Multiple workspaces", "Live DB connectors", "Approval workflows"] },
  { name: "Enterprise", price: "Contact us", features: ["SSO", "Dedicated support", "Custom SLAs"] },
];

/** No self-serve billing exists (out of scope per the PRD) -- every
 * tier routes to the same request-access flow. */
export function PricingPage() {
  return (
    <div style={{ maxWidth: "880px", margin: "0 auto", padding: "64px 32px" }}>
      <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>Pricing</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "40px" }}>
        Phase 0 has no self-serve billing -- every plan starts with a request-access conversation.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "20px" }}>
        {TIERS.map((tier) => (
          <div
            key={tier.name}
            style={{
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "24px",
              background: "var(--color-surface-raised)",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 600 }}>{tier.name}</h3>
            <p style={{ fontSize: "20px", fontWeight: 700, margin: "8px 0 16px", color: "var(--color-accent-strong)" }}>
              {tier.price}
            </p>
            <ul style={{ paddingLeft: "18px", color: "var(--color-text-muted)", fontSize: "13px" }}>
              {tier.features.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
