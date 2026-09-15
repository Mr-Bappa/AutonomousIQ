import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export interface TransformationJob {
  id: string;
  dataset_id: string;
  status: string;
  code_version: string;
  dataset_version: number;
  sample_used: boolean;
  approval_metadata: Record<string, unknown>;
  execution_target: string;
}

/** Matches GET /v1/approvals (apps/api/approvals.py). Will legitimately
 * return an empty list until the planner (apps/planner/, still unbuilt)
 * exists to create pending_approval jobs in the first place. */
export function usePendingApprovals() {
  return useQuery({
    queryKey: ["approvals"],
    queryFn: () => apiRequest<TransformationJob[]>("/v1/approvals"),
  });
}

export function useApproveJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      apiRequest<TransformationJob>(`/v1/approvals/${jobId}/approve`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });
}

export function useRejectJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      apiRequest<TransformationJob>(`/v1/approvals/${jobId}/reject`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });
}
