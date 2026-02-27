"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api";

interface StaffSession {
  session_id: string;
  session_type: string;
  created_at: string;
  last_active: string;
  message_count: number;
  shadow_mode: boolean;
}

export function useStaffSessions() {
  const { data: session } = useSession();
  const token = (session as Record<string, unknown> | null)?.apiToken as
    | string
    | undefined;

  return useQuery<StaffSession[]>({
    queryKey: ["staff-sessions"],
    queryFn: () => apiFetch("/staff/sessions", { token }),
    refetchInterval: 10_000,
    enabled: !!token,
  });
}
