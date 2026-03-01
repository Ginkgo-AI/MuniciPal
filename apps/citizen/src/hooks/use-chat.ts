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

interface SessionInfo {
  session_id: string;
  session_type: string;
  title: string | null;
  created_at: string;
  last_active: string;
  message_count: number;
}

interface SessionDetail extends SessionInfo {
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
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ session_id: string }>("/sessions", {
        method: "POST",
        body: JSON.stringify({ session_type: "anonymous" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
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
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

export function useSessionList() {
  return useQuery<SessionInfo[]>({
    queryKey: ["sessions"],
    queryFn: () => apiFetch("/sessions"),
    refetchInterval: 10_000,
  });
}

export function useRenameSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      title,
    }: {
      sessionId: string;
      title: string;
    }) =>
      apiFetch(`/sessions/${sessionId}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["session", variables.sessionId],
      });
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch(`/sessions/${sessionId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

export type { ChatMessage, SessionInfo, SessionDetail, ChatResponse };
