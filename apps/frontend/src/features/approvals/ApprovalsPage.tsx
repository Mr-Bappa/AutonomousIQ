import type { CSSProperties } from "react";
import { useApproveJob, usePendingApprovals, useRejectJob } from "./useApprovals";

/**
 * Real API wiring, but see apps/api/approvals.py's module docstring:
 * approve/reject here is tenant-scoped only, not the real is_approver
 * check the PRD describes -- and the queue will show nothing until a
 * planner exists to create pending_approval jobs in the first place.
 * This page is honest about that empty state rather than faking data.
 */
export function ApprovalsPage() {
  const { data, isLoading, isError, error } = usePendingApprovals();
  const approve = useApproveJob();
  const reject = useRejectJob();

  return (
    <div style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "4px" }}>Approvals</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "24px" }}>
        AI-proposed transformations waiting for a human decision before they run.
      </p>

      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading approvals…</p>}
      {isError && (
        <p style={{ color: "var(--color-negative)" }}>
          Couldn't load approvals: {(error as Error).message}
        </p>
      )}
      {data && data.length === 0 && (
        <p style={{ color: "var(--color-text-muted)" }}>
          Nothing pending. Jobs show up here once a transformation is proposed and awaiting review.
        </p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxWidth: "720px" }}>
        {data?.map((job) => (
          <div
            key={job.id}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px 16px",
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div>
              <div className="data-value" style={{ fontSize: "13px" }}>
                job {job.id.slice(0, 8)} · dataset {job.dataset_id.slice(0, 8)}
              </div>
              <div style={{ color: "var(--color-text-muted)", fontSize: "12px", marginTop: "2px" }}>
                code {job.code_version} · dataset v{job.dataset_version} ·{" "}
                {job.sample_used ? "sample" : "full data"} · {job.execution_target}
              </div>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => reject.mutate(job.id)}
                disabled={reject.isPending || approve.isPending}
                style={buttonStyle("var(--color-negative)")}
              >
                Reject
              </button>
              <button
                onClick={() => approve.mutate(job.id)}
                disabled={reject.isPending || approve.isPending}
                style={buttonStyle("var(--color-positive)")}
              >
                Approve
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function buttonStyle(borderColor: string): CSSProperties {
  return {
    padding: "6px 14px",
    background: "transparent",
    border: `1px solid ${borderColor}`,
    color: borderColor,
    borderRadius: "var(--radius-sm)",
    cursor: "pointer",
    fontSize: "13px",
  };
}
