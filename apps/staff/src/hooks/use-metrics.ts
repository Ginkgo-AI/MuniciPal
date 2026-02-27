"use client";

import { useQuery } from "@tanstack/react-query";
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
  return useQuery<MetricsSnapshot>({
    queryKey: ["metrics"],
    queryFn: () => apiFetch("/staff/metrics"),
    refetchInterval: 10_000,
  });
}
