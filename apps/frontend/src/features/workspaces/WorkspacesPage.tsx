import { useWorkspaces } from "./useWorkspaces";

export function WorkspacesPage() {
  const { data, isLoading, isError, error } = useWorkspaces();

  return (
    <div style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "4px" }}>Workspaces</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "24px" }}>
        Every workspace your tenant has access to.
      </p>

      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading workspaces…</p>}

      {isError && (
        <p style={{ color: "var(--color-negative)" }}>
          Couldn't load workspaces: {(error as Error).message}
        </p>
      )}

      {data && data.length === 0 && (
        <p style={{ color: "var(--color-text-muted)" }}>
          No workspaces yet. An Admin or Developer can create one.
        </p>
      )}

      {data && data.length > 0 && (
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "640px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ padding: "8px 12px", fontWeight: 500, color: "var(--color-text-muted)" }}>
                Name
              </th>
              <th style={{ padding: "8px 12px", fontWeight: 500, color: "var(--color-text-muted)" }}>
                Self-serve
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((workspace) => (
              <tr key={workspace.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: "8px 12px" }}>{workspace.name}</td>
                <td style={{ padding: "8px 12px" }} className="data-value">
                  {workspace.self_serve ? "yes" : "no"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
