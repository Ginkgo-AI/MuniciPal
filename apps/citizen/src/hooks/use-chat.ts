"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface ChatMessage {
  role: string;
  content: string;
  timestamp: string;
  citations: Array<Record<string, unknown>> | null;
  confidence: number | null;
  low_confidence: boolean | null;
}

interface SessionDetail {
  session_id: string;
  session_type: string;
  created_at: string;
  last_active: string;
  message_count: number;
  messages: ChatMessage[];
}

interface ChatResponse {
  response: string;
  citations: Array<Record<string, unknown>>;
  confidence: number;
  low_confidence: boolean;
}

export function useSession(sessionId: string | null) {
  return useQuery<SessionDetail>({
    queryKey: ["session", sessionId],
    queryFn: () => apiFetch(`/sessions/${sessionId}`),
    enabled: !!sessionId,
    refetchInterval: 5_000,
  });
}

export function useCreateSession() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ session_id: string }>("/sessions", {
        method: "POST",
        body: JSON.stringify({ session_type: "anonymous" }),
      }),
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      message,
    }: {
      sessionId: string;
      message: string;
    }) =>
      apiFetch<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, message }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["session", variables.sessionId],
      });
    },
  });
}
