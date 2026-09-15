import { useRef, type ChangeEvent } from "react";
import { useDocuments, useUploadDocument } from "./useDocuments";

export function DocumentsPage() {
  const { data, isLoading, isError, error } = useDocuments();
  const upload = useUploadDocument();
  const fileInput = useRef<HTMLInputElement>(null);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
    if (fileInput.current) fileInput.current.value = "";
  }

  return (
    <div style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "4px" }}>Documents</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "24px" }}>
        Uploaded documents feed the chat planner's document search. Only .txt/.md/.csv/.json
        uploads have their text extracted for search today -- other formats store but won't
        surface in search results yet.
      </p>

      <label
        style={{
          display: "inline-block",
          padding: "8px 16px",
          background: "var(--color-accent)",
          color: "#ffffff",
          borderRadius: "var(--radius-sm)",
          fontWeight: 600,
          fontSize: "13px",
          cursor: "pointer",
          marginBottom: "24px",
        }}
      >
        {upload.isPending ? "Uploading…" : "Upload document"}
        <input ref={fileInput} type="file" onChange={handleFileChange} style={{ display: "none" }} />
      </label>

      {isLoading && <p style={{ color: "var(--color-text-muted)" }}>Loading documents…</p>}
      {isError && <p style={{ color: "var(--color-negative)" }}>Couldn't load documents: {(error as Error).message}</p>}
      {data && data.length === 0 && <p style={{ color: "var(--color-text-muted)" }}>No documents yet.</p>}

      <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
        {data?.map((doc) => (
          <li
            key={doc.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "10px 12px",
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <span>{doc.name}</span>
            <span className="data-value" style={{ color: "var(--color-text-muted)", fontSize: "12px" }}>
              {doc.format} · {doc.has_extracted_text ? "searchable" : "not searchable"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
