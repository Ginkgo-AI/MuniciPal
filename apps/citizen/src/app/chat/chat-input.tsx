"use client";

import { useState, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { useCreateSession, useSendMessage } from "@/hooks/use-chat";
import { useLocaleContext } from "@/i18n/locale-context";
import { detectLanguage } from "@/lib/detect-language";
import { SendHorizontal } from "lucide-react";

export function ChatInput() {
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

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
        // The backend LLM may still be processing — the session poller will
        // pick up the response once it arrives. Show a soft message instead
        // of a hard error.
        setMessage("");
        setError("The response is taking longer than expected. Please wait a moment — it should appear shortly.");
        // Auto-clear after 10 seconds so the error message fades
        setTimeout(() => setError(null), 10_000);
      }
    },
    [message, sessionId, locale, createSession, sendMessage, setLocale, tCommon]
  );

  const isLoading = createSession.isPending || sendMessage.isPending;

  return (
    <div className="p-4 bg-gradient-to-t from-background via-background to-transparent z-10 w-full shrink-0">
      {error && (
        <p className="text-sm font-medium text-destructive mb-3 text-center bg-destructive/10 py-1.5 rounded-md px-3">{error}</p>
      )}
      <form
        ref={formRef}
        onSubmit={handleSubmit}
        className="max-w-3xl mx-auto flex items-end gap-2 bg-card border border-border/50 shadow-lg rounded-3xl p-2 pl-4 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/50 transition-all duration-200"
      >
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t("placeholder")}
          rows={1}
          disabled={isLoading}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              formRef.current?.requestSubmit();
            }
          }}
          className="flex-1 max-h-32 min-h-[44px] py-3 bg-transparent text-[0.95rem] placeholder:text-muted-foreground focus:outline-none resize-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading || !message.trim()}
          className="shrink-0 w-[44px] h-[44px] rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:opacity-90 disabled:opacity-50 disabled:scale-100 hover:scale-105 enabled:active:scale-95 transition-all duration-200 shadow-sm disabled:cursor-not-allowed mb-0.5"
        >
          {isLoading ? (
            <div className="w-5 h-5 flex items-center justify-center space-x-1">
              <div className="w-1 h-1 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-1 h-1 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-1 h-1 bg-current rounded-full animate-bounce"></div>
            </div>
          ) : (
            <SendHorizontal className="w-5 h-5 ml-0.5" strokeWidth={2.5} />
          )}
        </button>
      </form>
      <div className="text-center mt-3 mb-1">
        <p className="text-[11px] text-muted-foreground">
          {t("disclaimer")}
        </p>
      </div>
    </div>
  );
}
