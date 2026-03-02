import { Providers } from "@/lib/providers";
import { StatGrid } from "./stat-grid";
import { SystemStatus } from "./system-status";
import { RecentSessions } from "./recent-sessions";

export default function DashboardPage() {
  return (
    <Providers>
      <div className="max-w-7xl mx-auto p-6 lg:p-8 space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Mission Control
            </h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-0.5">
              Real-time operational metrics and system status
            </p>
          </div>
          <nav className="flex items-center gap-1 text-sm">
            <a
              href="/dashboard"
              className="px-3 py-1.5 rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)] font-medium"
            >
              Dashboard
            </a>
            <a
              href="/sessions"
              className="px-3 py-1.5 rounded-lg hover:bg-[var(--accent)] text-[var(--muted-foreground)] transition-colors"
            >
              Sessions
            </a>
          </nav>
        </header>

        {/* Metrics Grid */}
        <section>
          <StatGrid />
        </section>

        {/* System + Sessions */}
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <SystemStatus />
          </div>
          <div className="lg:col-span-3">
            <RecentSessions />
          </div>
        </div>
      </div>
    </Providers>
  );
}
