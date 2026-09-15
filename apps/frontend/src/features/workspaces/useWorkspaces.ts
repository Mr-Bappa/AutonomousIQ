import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export interface Workspace {
  id: string;
  name: string;
  self_serve: boolean;
}

/**
 * React Query owns all server state (STANDARDS.md Section 2) -- this is
 * the single source of truth for "what workspaces does this tenant
 * have", never mirrored into Zustand. Calls GET /v1/workspaces
 * (apps/api/workspaces.py), the same endpoint the Baseline stage used
 * to prove the backend's DB round trip -- this hook is that same proof
 * for the frontend.
 */
export function useWorkspaces() {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: () => apiRequest<Workspace[]>("/v1/workspaces"),
  });
}
