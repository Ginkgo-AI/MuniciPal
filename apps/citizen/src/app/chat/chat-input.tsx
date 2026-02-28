"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useCreateSession, useSendMessage } from "@/hooks/use-chat";
import { useLocaleContext } from "@/i18n/locale-context";
import { detectLanguage } from "@/lib/detect-language";
import { SendHorizontal } from "lucide-react";

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
    <div className="relative bottom-0 left-0 w-full bg-gradient-to-t from-background via-background/95 to-transparent pt-6 pb-6 px-4 md:px-8 mt-auto flex-shrink-0 z-10">
      <div className="max-w-4xl mx-auto">
        {error && (
          <p className="text-sm font-medium text-destructive mb-3 text-center bg-destructive/10 py-1.5 rounded-md px-3">{error}</p>
        )}
        <form
          onSubmit={handleSubmit}
          className="relative flex items-center shadow-lg shadow-indigo-500/5 hover:shadow-xl hover:shadow-indigo-500/10 transition-shadow duration-300 rounded-full border border-border/60 bg-card focus-within:ring-2 focus-within:ring-indigo-500/50 focus-within:border-indigo-500 overflow-hidden group"
        >
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t("placeholder")}
            disabled={isLoading}
            className="flex-1 bg-transparent px-6 py-4 text-[0.95rem] placeholder:text-muted-foreground outline-none disabled:opacity-50"
          />
          <div className="pr-3 pl-2 flex items-center">
            <button
              type="submit"
              disabled={isLoading || !message.trim()}
              className="p-2.5 rounded-full bg-indigo-600 text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-700 hover:shadow-lg disabled:opacity-50 disabled:shadow-none transition-all duration-200 active:scale-[0.95]"
            >
              <SendHorizontal className={`w-4 h-4 ${isLoading ? "animate-pulse" : ""}`} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
