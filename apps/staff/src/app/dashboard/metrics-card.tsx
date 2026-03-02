"use client";

import { ReactNode } from "react";

interface MetricsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  variant?: "default" | "success" | "warning" | "danger";
}

const variantStyles: Record<string, string> = {
  default: "border-[var(--border)]",
  success: "border-emerald-500/30 bg-emerald-500/5",
  warning: "border-amber-500/30 bg-amber-500/5",
  danger: "border-red-500/30 bg-red-500/5",
};

const valueColors: Record<string, string> = {
  default: "",
  success: "text-emerald-500",
  warning: "text-amber-500",
  danger: "text-red-500",
};

export function MetricsCard({
  title,
  value,
  subtitle,
  icon,
  variant = "default",
}: MetricsCardProps) {
  return (
    <div
      className={`rounded-xl border bg-[var(--card)] p-5 shadow-sm transition-all hover:shadow-md ${variantStyles[variant]}`}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-[var(--muted-foreground)]">
          {title}
        </p>
        {icon && (
          <div className="text-[var(--muted-foreground)] opacity-60">
            {icon}
          </div>
        )}
      </div>
      <p className={`mt-2 text-3xl font-bold tracking-tight ${valueColors[variant]}`}>
        {value}
      </p>
      {subtitle && (
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">
          {subtitle}
        </p>
      )}
    </div>
  );
}
