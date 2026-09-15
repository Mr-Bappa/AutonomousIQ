import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/shared/auth/AuthContext";
import { useUiStore } from "@/shared/store/uiStore";

const NAV_ITEMS = [
  { to: "/app/workspaces", label: "Workspaces" },
  { to: "/app/trackers", label: "Trackers" },
  { to: "/app/approvals", label: "Approvals" },
  { to: "/app/tickets", label: "Tickets" },
  { to: "/app/ingestion", label: "Ingestion" },
  { to: "/app/documents", label: "Documents" },
  { to: "/app/chat", label: "Chat / Planner" },
  { to: "/app/team", label: "Team" },
];

/**
 * The only piece of app/ built so far: a nav rail + content outlet. No
 * per-workspace switcher, no tenant name in the header, no notification
 * center -- those depend on features (workspaces beyond the list,
 * tenant settings) that aren't built yet, so this stays minimal rather
 * than faking chrome around empty pages.
 */
export function AppLayout() {
  const { logout } = useAuth();
  const { navCollapsed, toggleNav } = useUiStore();

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <nav
        style={{
          width: navCollapsed ? "56px" : "200px",
          transition: "width 150ms ease",
          background: "var(--color-surface-raised)",
          borderRight: "1px solid var(--color-border)",
          display: "flex",
          flexDirection: "column",
          padding: "16px 8px",
        }}
      >
        <button
          onClick={toggleNav}
          style={{
            background: "none",
            border: "none",
            color: "var(--color-text-muted)",
            textAlign: "left",
            padding: "8px",
            marginBottom: "16px",
            cursor: "pointer",
          }}
          aria-label="Toggle navigation width"
        >
          {navCollapsed ? "»" : "« AutonomousIQ"}
        </button>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "2px" }}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                color: isActive ? "var(--color-accent-strong)" : "var(--color-text)",
                background: isActive ? "var(--color-accent-soft)" : "transparent",
                textDecoration: "none",
                fontSize: "13px",
                whiteSpace: "nowrap",
                overflow: "hidden",
              })}
            >
              {navCollapsed ? item.label[0] : item.label}
            </NavLink>
          ))}
        </div>

        <button
          onClick={logout}
          style={{
            background: "none",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-muted)",
            borderRadius: "var(--radius-sm)",
            padding: "8px",
            cursor: "pointer",
            fontSize: "13px",
          }}
        >
          {navCollapsed ? "⏻" : "Sign out"}
        </button>
      </nav>

      <main style={{ flex: 1, overflow: "auto" }}>
        <Outlet />
      </main>
    </div>
  );
}
