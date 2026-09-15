import { useState, type FormEvent, type CSSProperties } from "react";
import { useConnectors, useCreateConnector, useTestConnector } from "./useConnectors";

const CONNECTOR_TYPES = ["postgres", "mysql", "sqlserver", "snowflake"] as const;

export function IngestionPage() {
  const { data: connectors, isLoading, isError, error } = useConnectors();
  const createConnector = useCreateConnector();
  const testConnector = useTestConnector();
  const [testResults, setTestResults] = useState<Record<string, string>>({});

  const [name, setName] = useState("");
  const [connectorType, setConnectorType] = useState<string>(CONNECTOR_TYPES[0]);
  const [host, setHost] = useState("");
  const [database, setDatabase] = useState("");
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createConnector.mutate(
      { connector_type: connectorType, name: name.trim(), config: { host, database, user, password } },
      { onSuccess: () => setName("") },
    );
  }

  function handleTest(id: string) {
    testConnector.mutate(id, {
      onSuccess: (result) => setTestResults((prev) => ({ ...prev, [id]: result.message })),
      onError: (err) => setTestResults((prev) => ({ ...prev, [id]: (err as Error).message })),
    });
  }

  return (
    <div style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "4px" }}>Ingestion</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "24px" }}>
        Connect a live database (D-3/D-13/D-14). Demo-level: each connector needs its real driver
        installed on the API server to actually connect -- "Test connection" will say so plainly if
        it's missing.
      </p>

      <form
        onSubmit={handleCreate}
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "8px",
          marginBottom: "24px",
          padding: "16px",
          background: "var(--color-surface-raised)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <select value={connectorType} onChange={(e) => setConnectorType(e.target.value)} style={inputStyle}>
          {CONNECTOR_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Connector name" style={inputStyle} />
        <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="Host" style={inputStyle} />
        <input value={database} onChange={(e) => setDatabase(e.target.value)} placeholder="Database" style={inputStyle} />
        <input value={user} onChange={(e) => setUser(e.target.value)} placeholder="User" style={inputStyle} />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          type="password"
          style={inputStyle}
        />
        <button type="submit" disabled={createConnector.isPending} style={buttonStyle}>
          {createConnector.isPending ? "Saving…" : "Save connector"}
        </button>
      </form>

      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading connectors…</p>}
      {isError && <p style={{ color: "var(--color-negative)" }}>Couldn't load connectors: {(error as Error).message}</p>}
      {connectors && connectors.length === 0 && <p style={{ color: "var(--color-text-muted)" }}>No connectors yet.</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {connectors?.map((c) => (
          <div
            key={c.id}
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
              <div>{c.name}</div>
              <div className="data-value" style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
                {c.connector_type}
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              {testResults[c.id] && (
                <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>{testResults[c.id]}</span>
              )}
              <button onClick={() => handleTest(c.id)} style={{ ...buttonStyle, background: "transparent", color: "var(--color-accent-strong)", border: "1px solid var(--color-accent)" }}>
                Test connection
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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
