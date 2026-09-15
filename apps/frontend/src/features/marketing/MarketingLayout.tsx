import { Link, NavLink, Outlet } from "react-router-dom";

const TABS = [
  { to: "/", label: "Home" },
  { to: "/product", label: "Product" },
  { to: "/pricing", label: "Pricing" },
  { to: "/about", label: "About" },
];

/**
 * Public marketing shell (unauthenticated) -- distinct from AppLayout,
 * which is the authenticated product shell. Kept deliberately simple:
 * one top nav bar, no footer mega-menu, no scroll animations. This is
 * the "full-fledged website with tabs" the person asked for, at demo
 * fidelity, not a production marketing site.
 */
export function MarketingLayout() {
  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 32px",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <Link to="/" style={{ textDecoration: "none", fontWeight: 700, fontSize: "18px", color: "var(--color-text)" }}>
          Autonomous<span style={{ color: "var(--color-accent-strong)" }}>IQ</span>
        </Link>

        <nav style={{ display: "flex", gap: "24px" }}>
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end
              style={({ isActive }) => ({
                textDecoration: "none",
                fontSize: "14px",
                color: isActive ? "var(--color-accent-strong)" : "var(--color-text-muted)",
                fontWeight: isActive ? 600 : 400,
              })}
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <div style={{ display: "flex", gap: "12px" }}>
          <Link
            to="/login"
            style={{
              textDecoration: "none",
              color: "var(--color-text)",
              fontSize: "14px",
              padding: "8px 14px",
            }}
          >
            Sign in
          </Link>
          <Link
            to="/request-access"
            style={{
              textDecoration: "none",
              background: "var(--color-accent)",
              color: "#ffffff",
              fontSize: "14px",
              fontWeight: 600,
              padding: "8px 16px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            Request access
          </Link>
        </div>
      </header>

      <main style={{ flex: 1 }}>
        <Outlet />
      </main>

      <footer
        style={{
          padding: "24px 32px",
          borderTop: "1px solid var(--color-border)",
          color: "var(--color-text-muted)",
          fontSize: "13px",
        }}
      >
        © {new Date().getFullYear()} AutonomousIQ. Phase 0 demo build.
      </footer>
    </div>
  );
}
