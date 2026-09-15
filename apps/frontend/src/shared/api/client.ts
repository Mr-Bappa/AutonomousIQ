/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * Two responsibilities, both load-bearing for everything built on top:
 *   1. Attach the JWT (from AuthContext's token store) as a Bearer
 *      header on every request -- callers never touch headers directly.
 *   2. Unwrap STANDARDS.md Section 3's error envelope
 *      ({ "error": { code, message, details } }) into a typed
 *      ApiError, so React Query's `error` object is always this shape
 *      rather than a raw fetch Response.
 *
 * Deliberately NOT using axios/ky -- one small wrapper over fetch is
 * enough for Phase 0's API surface, and keeps the dependency list per
 * STANDARDS.md Section 2 minimal.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  status: number;

  constructor(status: number, code: string, message: string, details: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Set by AuthContext on login/logout. A module-level variable (not
// React state) because the API client is called from React Query's
// queryFn/mutationFn, outside any component render -- it needs a
// synchronous, always-current read of "what's the token right now"
// without threading it through every hook call.
let currentToken: string | null = null;

export function setAuthToken(token: string | null): void {
  currentToken = token;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const envelope = payload?.error;
    throw new ApiError(
      response.status,
      envelope?.code ?? "UNKNOWN_ERROR",
      envelope?.message ?? "Something went wrong.",
      envelope?.details ?? {},
    );
  }

  return payload as T;
}
