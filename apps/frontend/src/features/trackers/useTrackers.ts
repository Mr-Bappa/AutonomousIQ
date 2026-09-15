import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export interface TrackerSummary {
  id: string;
  name: string;
  schema_definition: Record<string, unknown>;
}

export interface TrackerCellData {
  row_idx: number;
  col_idx: number;
  raw_value: string | null;
  formula: string | null;
  computed_value: string | null;
  error_state: "none" | "circular_reference" | "invalid_formula" | "upstream_error";
}

export interface TrackerDetail extends TrackerSummary {
  cells: TrackerCellData[];
}

interface CellEditInput {
  row_idx: number;
  col_idx: number;
  raw_value: string | null;
  formula: string | null;
}

/** Matches GET /v1/trackers (apps/api/trackers.py). */
export function useTrackerList() {
  return useQuery({
    queryKey: ["trackers"],
    queryFn: () => apiRequest<TrackerSummary[]>("/v1/trackers"),
  });
}

/** Matches POST /v1/trackers. Invalidates the list so a newly created
 * tracker shows up without a manual refetch call from the caller.
 * `workspaceId` is optional but strongly encouraged -- a tracker
 * created without one falls back to tenant-scoping-only access (see
 * apps/api/trackers.py's module docstring), so the create form always
 * offers a workspace picker rather than defaulting to skip it. */
export function useCreateTracker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, workspaceId }: { name: string; workspaceId?: string }) =>
      apiRequest<TrackerSummary>("/v1/trackers", {
        method: "POST",
        body: { name, schema_definition: {}, workspace_id: workspaceId || null },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trackers"] });
    },
  });
}

/** Matches GET /v1/trackers/{id} -- tracker metadata + every cell. */
export function useTracker(trackerId: string | undefined) {
  return useQuery({
    queryKey: ["trackers", trackerId],
    queryFn: () => apiRequest<TrackerDetail>(`/v1/trackers/${trackerId}`),
    enabled: trackerId !== undefined,
  });
}

/**
 * Matches PUT /v1/trackers/{id}/cells. The recalc engine runs
 * server-side and the response is the tracker's full fresh cell state
 * (every cell it touched during recalculation, not just the edited
 * one) -- so on success we write that response straight into the
 * ["trackers", trackerId] cache instead of invalidating and refetching.
 * This is the one place STANDARDS.md's "optimistic UI updates are fine,
 * silent client-side recalculation is not" boundary matters: we don't
 * compute the new value ourselves, we just paint whatever the backend
 * already recalculated.
 */
export function useEditCell(trackerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (edit: CellEditInput) =>
      apiRequest<TrackerDetail>(`/v1/trackers/${trackerId}/cells`, {
        method: "PUT",
        body: edit,
      }),
    onSuccess: (updatedTracker) => {
      queryClient.setQueryData(["trackers", trackerId], updatedTracker);
    },
  });
}
