"use client";

import { useMetrics } from "@/hooks/use-metrics";
import { MetricsCard } from "./metrics-card";

export function StatGrid() {
  const { data: metrics, isLoading, error } = useMetrics();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-28 rounded-xl border border-[var(--border)] bg-[var(--card)] animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6">
        <p className="text-sm font-medium text-red-400">
          ⚠ Unable to load metrics
        </p>
        <p className="text-xs text-[var(--muted-foreground)] mt-1">
          Make sure the backend is running on port 8080.
        </p>
      </div>
    );
  }

  if (!metrics) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricsCard
        title="Active Sessions"
        value={metrics.active_sessions}
        subtitle={`${metrics.total_sessions} total`}
        variant="success"
        icon={<svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>}
      />
      <MetricsCard
        title="Total Cases"
        value={metrics.total_cases}
        icon={<svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>}
      />
      <MetricsCard
        title="Pending Approvals"
        value={metrics.pending_approvals}
        subtitle={`${metrics.approved_count} approved · ${metrics.denied_count} denied`}
        variant={metrics.pending_approvals > 0 ? "warning" : "default"}
        icon={<svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>}
      />
      <MetricsCard
        title="LLM Latency"
        value={
          metrics.llm_latency_p50_ms != null
            ? `${metrics.llm_latency_p50_ms}ms`
            : "N/A"
        }
        subtitle={
          metrics.llm_latency_p95_ms != null
            ? `p95: ${metrics.llm_latency_p95_ms}ms`
            : "No data yet"
        }
        variant={
          metrics.llm_latency_p50_ms != null && metrics.llm_latency_p50_ms > 5000
            ? "danger"
            : "default"
        }
        icon={<svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>}
      />
    </div>
  );
}
