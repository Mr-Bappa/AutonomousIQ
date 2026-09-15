import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useWorkspaces } from "@/features/workspaces/useWorkspaces";
import { useCreateTracker, useTrackerList } from "./useTrackers";

export function TrackersPage() {
  const { data, isLoading, isError, error } = useTrackerList();
  const { data: workspaces } = useWorkspaces();
  const createTracker = useCreateTracker();
  const [name, setName] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createTracker.mutate({ name: name.trim(), workspaceId: workspaceId || undefined }, { onSuccess: () => setName("") });
  }

  return (
    <div style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "4px" }}>Trackers</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "24px" }}>
        Live-editable, formula-capable grids -- tenant-global (PRD Trackers). Bind a new tracker to
        a workspace so its access follows that workspace's grants, rather than falling back to
        tenant-wide access.
      </p>

      <form onSubmit={handleCreate} style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New tracker name"
          style={{
            padding: "8px 10px",
            background: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text)",
            fontSize: "14px",
            width: "200px",
          }}
        />
        <select
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
          style={{
            padding: "8px 10px",
            background: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text)",
            fontSize: "13px",
          }}
        >
          <option value="">No workspace (tenant-wide fallback)</option>
          {workspaces?.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={createTracker.isPending}
          style={{
            padding: "8px 16px",
            background: "var(--color-accent)",
            color: "#ffffff",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {createTracker.isPending ? "Creating…" : "Create"}
        </button>
      </form>

      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading trackers…</p>}
      {isError && (
        <p style={{ color: "var(--color-negative)" }}>
          Couldn't load trackers: {(error as Error).message}
        </p>
      )}
      {data && data.length === 0 && (
        <p style={{ color: "var(--color-text-muted)" }}>No trackers yet -- create one above.</p>
      )}

      <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
        {data?.map((tracker) => (
          <li key={tracker.id}>
            <Link
              to={`/app/trackers/${tracker.id}`}
              style={{
                display: "block",
                padding: "10px 12px",
                background: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                textDecoration: "none",
                color: "var(--color-text)",
              }}
            >
              {tracker.name}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
