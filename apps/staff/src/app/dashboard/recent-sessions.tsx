"use client";

import { useStaffSessions } from "@/hooks/use-sessions";

export function RecentSessions() {
    const { data: sessions, isLoading } = useStaffSessions();

    if (isLoading) {
        return (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5">
                <div className="h-6 w-40 bg-[var(--background)] rounded animate-pulse mb-4" />
                <div className="space-y-2">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="h-12 bg-[var(--background)] rounded-lg animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    const recent = (sessions ?? []).slice(0, 10);

    return (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
            <div className="px-5 py-4 border-b border-[var(--border)]">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Recent Sessions ({sessions?.length ?? 0})
                </h3>
            </div>
            {recent.length === 0 ? (
                <div className="p-6 text-center text-sm text-[var(--muted-foreground)]">
                    No active sessions
                </div>
            ) : (
                <div className="divide-y divide-[var(--border)]">
                    {recent.map((s) => (
                        <div
                            key={s.session_id}
                            className="flex items-center justify-between px-5 py-3 hover:bg-[var(--background)] transition-colors"
                        >
                            <div className="min-w-0">
                                <p className="text-sm font-medium truncate">
                                    {s.title || s.session_id.slice(0, 8)}
                                </p>
                                <p className="text-xs text-[var(--muted-foreground)]">
                                    {s.session_type} · {s.message_count} messages
                                </p>
                            </div>
                            <div className="text-right shrink-0 ml-4">
                                <p className="text-xs text-[var(--muted-foreground)]">
                                    {new Date(s.last_active).toLocaleString(undefined, {
                                        month: "short",
                                        day: "numeric",
                                        hour: "2-digit",
                                        minute: "2-digit",
                                    })}
                                </p>
                                {s.shadow_mode && (
                                    <span className="inline-block mt-0.5 text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 font-medium">
                                        Shadow
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
