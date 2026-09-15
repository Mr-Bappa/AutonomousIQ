import { useState, type FormEvent } from "react";
import { useSendChatMessage } from "./useChat";

interface Turn {
  role: "user" | "assistant";
  text: string;
  toolResults?: Array<{ tool_name: string; status: string; message?: string }>;
}

/**
 * The plain-transcript half of the PRD's "hybrid chat + editable
 * code/output cell" interaction model -- the editable-cell half (letting
 * someone tweak a proposed query/chart inline before it goes to
 * approval) isn't built in this pass. tool_results with
 * status="pending_approval" are shown as a badge only; approving them
 * happens on the Approvals page, not here.
 */
export function ChatPlannerPage() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const sendMessage = useSendChatMessage();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message) return;
    setInput("");
    setTurns((prev) => [...prev, { role: "user", text: message }]);

    sendMessage.mutate(
      { message, session_id: sessionId },
      {
        onSuccess: (response) => {
          setTurns((prev) => [
            ...prev,
            { role: "assistant", text: response.text, toolResults: response.tool_results },
          ]);
        },
        onError: (err) => {
          setTurns((prev) => [...prev, { role: "assistant", text: `Error: ${(err as Error).message}` }]);
        },
      },
    );
  }

  return (
    <div style={{ padding: "32px", height: "100%", display: "flex", flexDirection: "column" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "4px" }}>Chat / Planner</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "16px" }}>
        Ask about your documents, Trackers, or data. SQL, Tracker writes, and charts need approval
        before they run -- this is running in demo mode unless LLM_PROVIDER=vertex is configured.
      </p>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          padding: "16px",
          marginBottom: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {turns.length === 0 && (
          <p style={{ color: "var(--color-text-muted)", fontSize: "13px" }}>
            Try: "find the onboarding doc" or "chart last quarter's revenue".
          </p>
        )}
        {turns.map((turn, i) => (
          <div
            key={i}
            style={{
              alignSelf: turn.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "70%",
              background: turn.role === "user" ? "var(--color-accent-soft)" : "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "10px 14px",
              whiteSpace: "pre-wrap",
              fontSize: "14px",
            }}
          >
            {turn.text}
            {turn.toolResults?.some((r) => r.status === "pending_approval") && (
              <div
                style={{
                  marginTop: "8px",
                  fontSize: "11px",
                  color: "var(--color-accent-strong)",
                  fontWeight: 600,
                }}
              >
                ● Awaiting approval -- see the Approvals page
              </div>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "8px" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something…"
          style={{
            flex: 1,
            padding: "10px 12px",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text)",
            fontSize: "14px",
          }}
        />
        <button
          type="submit"
          disabled={sendMessage.isPending}
          style={{
            padding: "10px 20px",
            background: "var(--color-accent)",
            color: "#ffffff",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {sendMessage.isPending ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
