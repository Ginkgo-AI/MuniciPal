"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useSession, useCreateSession, useSendMessage } from "@/hooks/use-chat";
import { AlertCircle, FileText, MapPin, Sparkles, User, Building2 } from "lucide-react";

export function MessageList() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: session } = useSession(sessionId);
  const createSession = useCreateSession();
  const sendMessage = useSendMessage();
  const t = useTranslations("chat");
  const tCommon = useTranslations("common");

  useEffect(() => {
    const handler = (e: Event) => setSessionId((e as CustomEvent).detail);
    window.addEventListener("municipal:session", handler);
    return () => window.removeEventListener("municipal:session", handler);
  }, []);

  const handleSuggestedAction = async (prompt: string) => {
    setError(null);
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
      await sendMessage.mutateAsync({ sessionId: sid, message: prompt });
    } catch {
      setError(tCommon("error"));
    }
  };

  const suggestedActions = [
    {
      icon: AlertCircle,
      title: t("suggestReport"),
      prompt: t("suggestReportPrompt"),
      description: t("suggestReportDesc"),
    },
    {
      icon: FileText,
      title: t("suggestPermits"),
      prompt: t("suggestPermitsPrompt"),
      description: t("suggestPermitsDesc"),
    },
    {
      icon: MapPin,
      title: t("suggestExplore"),
      prompt: t("suggestExplorePrompt"),
      description: t("suggestExploreDesc"),
    },
  ];

  const messages = session?.messages ?? [];

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col justify-center max-w-2xl mx-auto w-full animate-in fade-in zoom-in-95 duration-500">
        <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 text-primary mb-6 mx-auto">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-center mb-2">{t("welcomeTitle")}</h2>
        <p className="text-center text-muted-foreground mb-8">
          {t("welcomeSubtitle")}
        </p>

        {error && (
          <p className="text-xs text-center text-[var(--destructive)] mb-4">{error}</p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {suggestedActions.map((action, i) => (
            <button
              key={i}
              onClick={() => handleSuggestedAction(action.prompt)}
              disabled={createSession.isPending || sendMessage.isPending}
              className="flex flex-col items-start p-4 text-left border rounded-xl bg-card hover:bg-accent hover:border-primary/50 transition-all duration-200 hover:shadow-md enabled:active:scale-95 disabled:opacity-50 disabled:scale-100 group"
            >
              <action.icon className="w-5 h-5 text-primary mb-3 group-hover:scale-110 transition-transform" />
              <h3 className="font-semibold text-sm mb-1">{action.title}</h3>
              <p className="text-xs text-muted-foreground line-clamp-2">{action.description}</p>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-[1_1_0%] overflow-y-auto p-4 space-y-6">
      {messages.map((msg, i) => {
        const isUser = msg.role === "user";
        return (
          <div
            key={i}
            className={`flex items-end gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300 ${isUser ? "justify-end" : "justify-start"
              }`}
          >
            {!isUser && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20">
                <Building2 className="w-4 h-4 text-primary" />
              </div>
            )}

            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-3.5 text-[0.95rem] leading-relaxed shadow-sm ${isUser
                ? "bg-primary text-primary-foreground rounded-br-sm"
                : "bg-card border border-border text-foreground rounded-bl-sm"
                }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/50 flex flex-wrap gap-2">
                  {msg.citations.map((cite, idx) => (
                    <div key={idx} className="inline-flex items-center px-2 py-1 rounded-md bg-muted text-xs font-medium text-muted-foreground border border-border/50">
                      <FileText className="w-3 h-3 mr-1.5 opacity-70" />
                      {String(cite.source)}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {isUser && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center border border-border">
                <User className="w-4 h-4 text-secondary-foreground" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
