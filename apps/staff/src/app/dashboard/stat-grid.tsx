"use client";

import { useMetrics } from "@/hooks/use-metrics";
import { MetricsCard } from "./metrics-card";

export function StatGrid() {
  const { data: metrics, isLoading, error } = useMetrics();

  if (isLoading) {
    return <p className="text-[var(--muted-foreground)]">Loading metrics...</p>;
  }

  if (error) {
    return (
      <p className="text-[var(--destructive)]">
        Unable to load metrics. Make sure the backend is running and you are authenticated.
      </p>
    );
  }

  if (!metrics) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricsCard
        title="Active Sessions"
        value={metrics.active_sessions}
        subtitle={`${metrics.total_sessions} total`}
      />
      <MetricsCard title="Total Cases" value={metrics.total_cases} />
      <MetricsCard
        title="Pending Approvals"
        value={metrics.pending_approvals}
        subtitle={`${metrics.approved_count} approved, ${metrics.denied_count} denied`}
      />
      <MetricsCard
        title="LLM Latency (p50)"
        value={
          metrics.llm_latency_p50_ms != null
            ? `${metrics.llm_latency_p50_ms}ms`
            : "N/A"
        }
        subtitle={
          metrics.llm_latency_p95_ms != null
            ? `p95: ${metrics.llm_latency_p95_ms}ms`
            : undefined
        }
      />
      {metrics.shadow_divergence_rate != null && (
        <MetricsCard
          title="Shadow Divergence"
          value={`${(metrics.shadow_divergence_rate * 100).toFixed(1)}%`}
        />
      )}
    </div>
  );
}
