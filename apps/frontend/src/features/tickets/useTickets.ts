import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export interface Ticket {
  id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  category: string;
  status: "open" | "in_progress" | "resolved" | "closed";
}

export function useTickets() {
  return useQuery({
    queryKey: ["tickets"],
    queryFn: () => apiRequest<Ticket[]>("/v1/tickets"),
  });
}

export function useCreateTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { workspace_id: string; title: string; category: string }) =>
      apiRequest<Ticket>("/v1/tickets", { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tickets"] }),
  });
}

export function useUpdateTicketStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: Ticket["status"] }) =>
      apiRequest<Ticket>(`/v1/tickets/${id}`, { method: "PATCH", body: { status } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tickets"] }),
  });
}
