import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

export interface DocumentSummary {
  id: string;
  name: string;
  format: string;
  has_extracted_text: boolean;
}

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: () => apiRequest<DocumentSummary[]>("/v1/documents"),
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      // apiRequest assumes JSON bodies -- multipart needs its own fetch call.
      const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
      const token = sessionStorage.getItem("autonomousiq_token");
      const response = await fetch(`${base}/v1/documents`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      if (!response.ok) throw new Error("Upload failed.");
      return response.json() as Promise<DocumentSummary>;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
}
