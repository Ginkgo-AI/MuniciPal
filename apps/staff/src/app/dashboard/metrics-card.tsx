"use client";

interface MetricsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
}

export function MetricsCard({ title, value, subtitle }: MetricsCardProps) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-sm">
      <p className="text-sm font-medium text-[var(--muted-foreground)]">
        {title}
      </p>
      <p className="mt-2 text-3xl font-bold tracking-tight">{value}</p>
      {subtitle && (
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">
          {subtitle}
        </p>
      )}
    </div>
  );
}
