import { useState, type FormEvent, type CSSProperties } from "react";
import {
  useApproveTenantRequest,
  useCreateTeam,
  useInviteUser,
  useRejectTenantRequest,
  useTeams,
  useTenantRequests,
  useUsers,
} from "./useTeam";

export function TeamPage() {
  return (
    <div style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "40px" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600 }}>Team</h1>
      <UsersSection />
      <TeamsSection />
      <TenantRequestsSection />
    </div>
  );
}

function UsersSection() {
  const { data: users, isLoading } = useUsers();
  const { data: teams } = useTeams();
  const invite = useInviteUser();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [teamId, setTeamId] = useState("");
  const [lastTempPassword, setLastTempPassword] = useState<string | null>(null);

  function handleInvite(e: FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    invite.mutate(
      { email: email.trim(), role, team_id: teamId || undefined },
      {
        onSuccess: (result) => {
          setEmail("");
          setLastTempPassword(result.temporary_password);
        },
      },
    );
  }

  return (
    <section>
      <h2 style={sectionHeadingStyle}>Users</h2>
      <form onSubmit={handleInvite} style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" style={inputStyle} />
        <select value={role} onChange={(e) => setRole(e.target.value)} style={inputStyle}>
          <option value="admin">admin</option>
          <option value="developer">developer</option>
          <option value="viewer">viewer</option>
        </select>
        <select value={teamId} onChange={(e) => setTeamId(e.target.value)} style={inputStyle}>
          <option value="">No team</option>
          {teams?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <button type="submit" disabled={invite.isPending} style={buttonStyle}>
          {invite.isPending ? "Inviting…" : "Invite"}
        </button>
      </form>
      {lastTempPassword && (
        <p style={{ fontSize: "12px", color: "var(--color-accent-strong)", marginBottom: "12px" }}>
          Temporary password for the new user (demo -- no email system exists yet):{" "}
          <code className="data-value">{lastTempPassword}</code>
        </p>
      )}
      {invite.isError && (
        <p style={{ fontSize: "12px", color: "var(--color-negative)", marginBottom: "12px" }}>
          {(invite.error as Error).message}
        </p>
      )}
      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading users…</p>}
      <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
        {users?.map((u) => (
          <li key={u.id} style={rowStyle}>
            <span>{u.email}</span>
            <span className="data-value" style={{ color: "var(--color-text-muted)", fontSize: "12px" }}>
              {u.role}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function TeamsSection() {
  const { data: teams, isLoading } = useTeams();
  const createTeam = useCreateTeam();
  const [name, setName] = useState("");

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createTeam.mutate(name.trim(), { onSuccess: () => setName("") });
  }

  return (
    <section>
      <h2 style={sectionHeadingStyle}>Teams</h2>
      <form onSubmit={handleCreate} style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Team name" style={inputStyle} />
        <button type="submit" disabled={createTeam.isPending} style={buttonStyle}>
          {createTeam.isPending ? "Creating…" : "Create team"}
        </button>
      </form>
      {createTeam.isError && (
        <p style={{ fontSize: "12px", color: "var(--color-negative)", marginBottom: "12px" }}>
          {(createTeam.error as Error).message}
        </p>
      )}
      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading teams…</p>}
      <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
        {teams?.map((t) => (
          <li key={t.id} style={rowStyle}>
            <span>{t.name}</span>
            {t.archived && <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>archived</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function TenantRequestsSection() {
  const { data: requests, isLoading, isError } = useTenantRequests();
  const approve = useApproveTenantRequest();
  const reject = useRejectTenantRequest();
  const [approvedInfo, setApprovedInfo] = useState<{ email: string; password: string } | null>(null);

  if (isError) {
    // 403 for non-Admins -- this section simply doesn't render for them.
    return null;
  }

  return (
    <section>
      <h2 style={sectionHeadingStyle}>Tenant access requests (Admin only)</h2>
      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading requests…</p>}
      {requests && requests.length === 0 && <p style={{ color: "var(--color-text-muted)" }}>Nothing pending.</p>}
      {approvedInfo && (
        <p style={{ fontSize: "12px", color: "var(--color-accent-strong)", marginBottom: "12px" }}>
          Provisioned {approvedInfo.email} -- temporary password (demo, no email system):{" "}
          <code className="data-value">{approvedInfo.password}</code>
        </p>
      )}
      <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
        {requests
          ?.filter((r) => r.status === "pending")
          .map((r) => (
            <li key={r.id} style={rowStyle}>
              <span>
                {r.company_name} <span style={{ color: "var(--color-text-muted)" }}>({r.contact_info})</span>
              </span>
              <span style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={() => reject.mutate(r.id)}
                  style={{ ...buttonStyle, background: "transparent", color: "var(--color-negative)", border: "1px solid var(--color-negative)" }}
                >
                  Reject
                </button>
                <button
                  onClick={() =>
                    approve.mutate(r.id, {
                      onSuccess: (result) =>
                        setApprovedInfo({ email: result.admin_email, password: result.temporary_password }),
                    })
                  }
                  style={buttonStyle}
                >
                  Approve
                </button>
              </span>
            </li>
          ))}
      </ul>
    </section>
  );
}

const sectionHeadingStyle: CSSProperties = { fontSize: "15px", fontWeight: 600, marginBottom: "12px" };

const rowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  padding: "10px 12px",
  background: "var(--color-surface-raised)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
};

const inputStyle: CSSProperties = {
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
  fontSize: "13px",
};
