import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export interface TeamUser {
  id: string;
  email: string;
  role: "admin" | "developer" | "viewer";
}

export interface Team {
  id: string;
  name: string;
  archived: boolean;
}

export interface TenantRequestSummary {
  id: string;
  company_name: string;
  contact_info: string;
  status: string;
}

export function useUsers() {
  return useQuery({ queryKey: ["users"], queryFn: () => apiRequest<TeamUser[]>("/v1/users") });
}

export function useInviteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { email: string; role: string; team_id?: string }) =>
      apiRequest<{ temporary_password: string }>("/v1/users", { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useTeams() {
  return useQuery({ queryKey: ["teams"], queryFn: () => apiRequest<Team[]>("/v1/teams") });
}

export function useCreateTeam() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => apiRequest<Team>("/v1/teams", { method: "POST", body: { name } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["teams"] }),
  });
}

/** Admin-only on the backend; a non-Admin will just get a 403 from
 * this query, surfaced as isError. */
export function useTenantRequests() {
  return useQuery({
    queryKey: ["tenant-requests"],
    queryFn: () => apiRequest<TenantRequestSummary[]>("/v1/tenant-requests"),
    retry: false,
  });
}

export function useApproveTenantRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiRequest<{ admin_email: string; temporary_password: string }>(`/v1/tenant-requests/${id}/approve`, {
        method: "POST",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenant-requests"] }),
  });
}

export function useRejectTenantRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiRequest(`/v1/tenant-requests/${id}/reject`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenant-requests"] }),
  });
}
