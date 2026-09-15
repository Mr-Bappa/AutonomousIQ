import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";

interface ChatResponse {
  session_id: string;
  message_id: string;
  intent: string;
  text: string;
  tool_results: Array<{ tool_name: string; status: string; message?: string; [key: string]: unknown }>;
}

export function useSendChatMessage() {
  return useMutation({
    mutationFn: (input: { message: string; session_id?: string }) =>
      apiRequest<ChatResponse>("/v1/chat", { method: "POST", body: input }),
  });
}

export type { ChatResponse };
