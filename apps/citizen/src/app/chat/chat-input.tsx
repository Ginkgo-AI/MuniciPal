"use client";

import { useState, useCallback } from "react";
import { useCreateSession, useSendMessage } from "@/hooks/use-chat";

export function ChatInput() {
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);

  const createSession = useCreateSession();
  const sendMessage = useSendMessage();

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!message.trim()) return;

      let sid = sessionId;
      if (!sid) {
        const result = await createSession.mutateAsync();
        sid = result.session_id;
        setSessionId(sid);
        // Store for MessageList
        window.dispatchEvent(
          new CustomEvent("municipal:session", { detail: sid })
        );
      }

      await sendMessage.mutateAsync({ sessionId: sid, message });
      setMessage("");
    },
    [message, sessionId, createSession, sendMessage]
  );

  const isLoading = createSession.isPending || sendMessage.isPending;

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-[var(--border)] p-4 flex gap-2"
    >
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your question..."
        disabled={isLoading}
        className="flex-1 rounded-md border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
      />
      <button
        type="submit"
        disabled={isLoading || !message.trim()}
        className="rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] px-4 py-2 text-sm font-medium shadow hover:opacity-90 disabled:opacity-50 transition"
      >
        {isLoading ? "..." : "Send"}
      </button>
    </form>
  );
}
