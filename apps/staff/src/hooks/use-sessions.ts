"use client";

import { useQuery } from "@tanstack/react-query";
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
  return useQuery<StaffSession[]>({
    queryKey: ["staff-sessions"],
    queryFn: () => apiFetch("/staff/sessions"),
    refetchInterval: 10_000,
  });
}
