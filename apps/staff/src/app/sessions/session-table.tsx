"use client";

import { useStaffSessions } from "@/hooks/use-sessions";

export function SessionTable() {
  const { data: sessions, isLoading, error } = useStaffSessions();

  if (isLoading) {
    return <p className="text-[var(--muted-foreground)]">Loading sessions...</p>;
  }

  if (error) {
    return (
      <p className="text-[var(--destructive)]">
        Unable to load sessions. Make sure the backend is running and you are authenticated.
      </p>
    );
  }

  if (!sessions || sessions.length === 0) {
    return <p className="text-[var(--muted-foreground)]">No active sessions.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
      <table className="w-full text-sm">
        <thead className="bg-[var(--secondary)]">
          <tr>
            <th className="text-left px-4 py-3 font-medium">Session ID</th>
            <th className="text-left px-4 py-3 font-medium">Type</th>
            <th className="text-left px-4 py-3 font-medium">Messages</th>
            <th className="text-left px-4 py-3 font-medium">Last Active</th>
            <th className="text-left px-4 py-3 font-medium">Shadow</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {sessions.map((s) => (
            <tr key={s.session_id} className="hover:bg-[var(--accent)]">
              <td className="px-4 py-3 font-mono text-xs">
                {s.session_id.slice(0, 8)}...
              </td>
              <td className="px-4 py-3">{s.session_type}</td>
              <td className="px-4 py-3">{s.message_count}</td>
              <td className="px-4 py-3 text-[var(--muted-foreground)]">
                {new Date(s.last_active).toLocaleString()}
              </td>
              <td className="px-4 py-3">
                {s.shadow_mode ? (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                    Active
                  </span>
                ) : (
                  <span className="text-xs text-[var(--muted-foreground)]">Off</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
