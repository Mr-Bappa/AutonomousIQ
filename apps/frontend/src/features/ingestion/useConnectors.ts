import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export interface ConnectorConfig {
  id: string;
  connector_type: "postgres" | "mysql" | "sqlserver" | "snowflake";
  name: string;
}

export function useConnectors() {
  return useQuery({
    queryKey: ["connectors"],
    queryFn: () => apiRequest<ConnectorConfig[]>("/v1/ingestion/connectors"),
  });
}

export function useCreateConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { connector_type: string; name: string; config: Record<string, unknown> }) =>
      apiRequest<ConnectorConfig>("/v1/ingestion/connectors", { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connectors"] }),
  });
}

export function useTestConnector() {
  return useMutation({
    mutationFn: (id: string) =>
      apiRequest<{ ok: boolean; message: string }>(`/v1/ingestion/connectors/${id}/test`, { method: "POST" }),
  });
}
