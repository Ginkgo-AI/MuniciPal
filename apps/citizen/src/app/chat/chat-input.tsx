"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useCreateSession, useSendMessage } from "@/hooks/use-chat";
import { useLocaleContext } from "@/i18n/locale-context";
import { detectLanguage } from "@/lib/detect-language";

export function ChatInput() {
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const t = useTranslations("chat");
  const tCommon = useTranslations("common");
  const { locale, setLocale } = useLocaleContext();

  const createSession = useCreateSession();
  const sendMessage = useSendMessage();

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!message.trim()) return;
      setError(null);

      const currentMessage = message;

      try {
        let sid = sessionId;
        if (!sid) {
          const result = await createSession.mutateAsync();
          sid = result.session_id;
          setSessionId(sid);
          window.dispatchEvent(
            new CustomEvent("municipal:session", { detail: sid })
          );
        }

        await sendMessage.mutateAsync({ sessionId: sid, message: currentMessage });
        setMessage("");

        // Detect language after successful send to avoid disorienting switch on failure
        const detected = detectLanguage(currentMessage);
        if (detected && detected !== locale) {
          setLocale(detected);
        }
      } catch {
        setError(tCommon("error"));
      }
    },
    [message, sessionId, locale, createSession, sendMessage, setLocale, tCommon]
  );

  const isLoading = createSession.isPending || sendMessage.isPending;

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-[var(--border)] p-4 flex flex-col gap-2"
    >
      {error && (
        <p className="text-xs text-[var(--destructive)]">{error}</p>
      )}
      <div className="flex gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t("placeholder")}
          disabled={isLoading}
          className="flex-1 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-1 transition-shadow"
        />
        <button
          type="submit"
          disabled={isLoading || !message.trim()}
          className="rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)] px-5 py-2 text-sm font-medium shadow-md shadow-[var(--primary)]/15 hover:shadow-lg hover:-translate-y-px disabled:opacity-50 disabled:shadow-none disabled:translate-y-0 transition-all duration-200"
        >
          {isLoading ? "..." : tCommon("send")}
        </button>
      </div>
    </form>
  );
}
