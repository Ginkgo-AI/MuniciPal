"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api";

export interface StaffSession {
  session_id: string;
  session_type: string;
  title?: string | null;
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
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}
