"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api";

interface MetricsSnapshot {
  total_sessions: number;
  active_sessions: number;
  total_cases: number;
  pending_approvals: number;
  approved_count: number;
  denied_count: number;
  adapter_health: Record<string, string>;
  llm_latency_p50_ms: number | null;
  llm_latency_p95_ms: number | null;
  shadow_divergence_rate: number | null;
  timestamp: string;
}

export function useMetrics() {
  const { data: session } = useSession();
  const token = (session as Record<string, unknown> | null)?.apiToken as
    | string
    | undefined;

  return useQuery<MetricsSnapshot>({
    queryKey: ["metrics"],
    queryFn: () => apiFetch("/staff/metrics", { token }),
    refetchInterval: 10_000,
    enabled: !!token,
  });
}
