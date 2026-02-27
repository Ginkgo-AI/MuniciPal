import { Providers } from "@/lib/providers";
import { MetricsCard } from "./metrics-card";
import { StatGrid } from "./stat-grid";

export default function DashboardPage() {
  return (
    <Providers>
      <div className="max-w-6xl mx-auto p-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-[var(--muted-foreground)] mt-1">
            Real-time operational metrics
          </p>
        </header>
        <StatGrid />
      </div>
    </Providers>
  );
}
