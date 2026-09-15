import { useState, type FormEvent, type CSSProperties } from "react";
import { useWorkspaces } from "@/features/workspaces/useWorkspaces";
import { useCreateTicket, useTickets, useUpdateTicketStatus, type Ticket } from "./useTickets";

const STATUS_OPTIONS: Ticket["status"][] = ["open", "in_progress", "resolved", "closed"];

export function TicketsPage() {
  const { data: tickets, isLoading, isError, error } = useTickets();
  const { data: workspaces } = useWorkspaces();
  const createTicket = useCreateTicket();
  const updateStatus = useUpdateTicketStatus();

  const [title, setTitle] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !workspaceId) return;
    createTicket.mutate(
      { workspace_id: workspaceId, title: title.trim(), category: "general" },
      { onSuccess: () => setTitle("") },
    );
  }

  return (
    <div style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "4px" }}>Tickets</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "24px" }}>
        Workspace-scoped tickets.
      </p>

      <form onSubmit={handleCreate} style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        <select
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
          style={selectStyle}
        >
          <option value="">Select workspace…</option>
          {workspaces?.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ticket title"
          style={{ ...selectStyle, width: "240px" }}
        />
        <button type="submit" disabled={createTicket.isPending} style={buttonStyle}>
          {createTicket.isPending ? "Creating…" : "Create"}
        </button>
      </form>

      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading tickets…</p>}
      {isError && <p style={{ color: "var(--color-negative)" }}>Couldn't load tickets: {(error as Error).message}</p>}
      {tickets && tickets.length === 0 && <p style={{ color: "var(--color-text-muted)" }}>No tickets yet.</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {tickets?.map((ticket) => (
          <div
            key={ticket.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 16px",
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div>
              <div>{ticket.title}</div>
              <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>{ticket.category}</div>
            </div>
            <select
              value={ticket.status}
              onChange={(e) => updateStatus.mutate({ id: ticket.id, status: e.target.value as Ticket["status"] })}
              style={selectStyle}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}

const selectStyle: CSSProperties = {
  padding: "8px 10px",
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
  color: "var(--color-text)",
  fontSize: "13px",
};

const buttonStyle: CSSProperties = {
  padding: "8px 16px",
  background: "var(--color-accent)",
  color: "#ffffff",
  border: "none",
  borderRadius: "var(--radius-sm)",
  fontWeight: 600,
  cursor: "pointer",
};
