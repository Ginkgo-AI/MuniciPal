"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useSession } from "@/hooks/use-chat";

export function MessageList() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { data: session } = useSession(sessionId);
  const t = useTranslations("chat");

  useEffect(() => {
    const handler = (e: Event) => {
      setSessionId((e as CustomEvent).detail);
    };
    window.addEventListener("municipal:session", handler);
    return () => window.removeEventListener("municipal:session", handler);
  }, []);

  const messages = session?.messages ?? [];

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--muted-foreground)] text-sm">
        {t("empty")}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
              msg.role === "user"
                ? "bg-[var(--primary)] text-[var(--primary-foreground)] rounded-br-md"
                : "bg-[var(--secondary)] text-[var(--secondary-foreground)] rounded-bl-md"
            }`}
          >
            <p className="whitespace-pre-wrap">{msg.content}</p>
            {msg.citations && msg.citations.length > 0 && (
              <div className="mt-2 pt-2 border-t border-current/10 text-xs opacity-75">
                {t("sourcesCited", { count: msg.citations.length })}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
