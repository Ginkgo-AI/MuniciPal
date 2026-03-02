"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface LoadedModel {
    name: string;
    size_gb: number;
    context_length: number;
}

interface SystemResources {
    total_ram_gb: number;
    available_ram_gb: number;
    ram_usage_percent: number;
    cpu_count: number;
    gpu_available: boolean;
    gpu_name: string;
    platform: string;
}

export function SystemStatus() {
    const { data: loaded } = useQuery<{ models: LoadedModel[] }>({
        queryKey: ["staff-loaded-models"],
        queryFn: () => apiFetch("/models/loaded"),
        staleTime: 30_000,
        refetchInterval: 30_000,
        refetchIntervalInBackground: false,
    });

    const { data: resources } = useQuery<SystemResources>({
        queryKey: ["staff-resources"],
        queryFn: () => apiFetch("/system/resources"),
        staleTime: 30_000,
        refetchInterval: 30_000,
        refetchIntervalInBackground: false,
    });

    return (
        <div className="grid gap-4 lg:grid-cols-2">
            {/* Loaded Models */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
                    Loaded Models
                </h3>
                {loaded?.models && loaded.models.length > 0 ? (
                    <div className="space-y-2">
                        {loaded.models.map((m) => (
                            <div
                                key={m.name}
                                className="flex items-center justify-between px-3 py-2 rounded-lg bg-[var(--background)] border border-[var(--border)]"
                            >
                                <div className="flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                                    <span className="text-sm font-medium">{m.name}</span>
                                </div>
                                <span className="text-xs text-[var(--muted-foreground)]">
                                    {m.size_gb} GB · ctx {m.context_length}
                                </span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-sm text-[var(--muted-foreground)]">
                        No models currently loaded
                    </p>
                )}
            </div>

            {/* System Resources */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
                    System Resources
                </h3>
                {resources ? (
                    <div className="space-y-3">
                        <div>
                            <div className="flex items-center justify-between text-sm mb-1">
                                <span className="text-[var(--muted-foreground)]">RAM</span>
                                <span className="font-medium">
                                    {resources.available_ram_gb} / {resources.total_ram_gb} GB free
                                </span>
                            </div>
                            <div className="h-2 rounded-full bg-[var(--background)] overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all ${resources.ram_usage_percent > 85
                                            ? "bg-red-500"
                                            : resources.ram_usage_percent > 70
                                                ? "bg-amber-500"
                                                : "bg-emerald-500"
                                        }`}
                                    style={{ width: `${resources.ram_usage_percent}%` }}
                                />
                            </div>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-[var(--muted-foreground)]">CPU</span>
                            <span className="font-medium">{resources.cpu_count} cores</span>
                        </div>
                        {resources.gpu_available && (
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-[var(--muted-foreground)]">GPU</span>
                                <span className="font-medium">{resources.gpu_name}</span>
                            </div>
                        )}
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-[var(--muted-foreground)]">Platform</span>
                            <span className="font-medium text-xs">{resources.platform}</span>
                        </div>
                    </div>
                ) : (
                    <p className="text-sm text-[var(--muted-foreground)]">Loading...</p>
                )}
            </div>
        </div>
    );
}
