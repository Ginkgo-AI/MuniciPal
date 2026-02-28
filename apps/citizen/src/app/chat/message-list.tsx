"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useSession, useCreateSession, useSendMessage } from "@/hooks/use-chat";
import { Sparkles, AlertCircle, FileText, MapPin, CreditCard, Archive, CheckSquare, Users, BookOpen, User, Building2 } from "lucide-react";
import { Card, CardContent } from "@municipal/ui";

const GRID_SERVICES = [
  { id: "reportIssue", icon: AlertCircle, prompt: "I need to report an issue." },
  { id: "permits", icon: FileText, prompt: "I need help with a permit or license." },
  { id: "exploreParks", icon: MapPin, prompt: "Tell me about local parks and recreation." },
  { id: "payBill", icon: CreditCard, prompt: "How do I pay my utility bill?" },
  { id: "publicRecords", icon: Archive, prompt: "I want to submit a FOIA public records request." },
  { id: "voting", icon: CheckSquare, prompt: "How do I register to vote?" },
  { id: "cityCouncil", icon: Users, prompt: "When is the next city council meeting?" },
  { id: "library", icon: BookOpen, prompt: "What are the library hours and services?" },
] as const;

export function MessageList() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { data: session } = useSession(sessionId);
  const createSession = useCreateSession();
  const sendMessage = useSendMessage();
  const t = useTranslations("chat");

  useEffect(() => {
    const handler = (e: Event) => setSessionId((e as CustomEvent).detail);
    window.addEventListener("municipal:session", handler);
    return () => window.removeEventListener("municipal:session", handler);
  }, []);

  const handleSuggestedAction = async (prompt: string) => {
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
  };

  const messages = session?.messages ?? [];

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col justify-center w-full animate-in fade-in zoom-in-95 duration-500 max-w-4xl mx-auto items-center">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-500 text-white mb-4 shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-semibold tracking-tight text-center mb-2 px-4 text-foreground">{t("welcome")}</h2>
          <p className="text-center text-muted-foreground max-w-lg px-4 text-sm leading-relaxed">
            {t("welcomeDesc")}
          </p>
        </div>

        {/* Apple-style Compact Grid with Shadcn Cards */}
        <div className="w-full px-2 sm:px-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 w-full">
            {GRID_SERVICES.map((action) => (
              <Card
                key={action.id}
                onClick={() => handleSuggestedAction(action.prompt)}
                className="group cursor-pointer hover:border-indigo-500/30 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 active:scale-[0.98] outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 bg-background/60 dark:bg-card/40 border-border/40"
                role="button"
                tabIndex={0}
                onKeyDown={(e: React.KeyboardEvent<HTMLDivElement>) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSuggestedAction(action.prompt);
                  }
                }}
              >
                <CardContent className="p-4 flex flex-col h-full pointer-events-none">
                  <div className="flex items-center gap-3 mb-2 w-full">
                    <div className="w-8 h-8 flex-shrink-0 rounded-full bg-secondary text-secondary-foreground flex items-center justify-center group-hover:bg-indigo-500 group-hover:text-white transition-colors duration-200 shadow-sm border border-border/50">
                      <action.icon className="w-4 h-4" />
                    </div>
                    <h3 className="font-semibold text-[0.85rem] leading-tight text-foreground group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors duration-200 break-words">{t(`services.${action.id}`)}</h3>
                  </div>
                  <p className="text-[0.7rem] text-muted-foreground leading-snug mt-auto">
                    {action.prompt}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-[1_1_0%] overflow-y-auto p-4 md:p-6 space-y-6">
      {messages.map((msg, i) => {
        const isUser = msg.role === "user";
        return (
          <div
            key={i}
            className={`flex items-end gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300 ${isUser ? "justify-end" : "justify-start"
              }`}
          >
            {!isUser && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 shadow-sm hidden sm:flex">
                <Building2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              </div>
            )}

            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-[20px] px-5 py-3.5 text-[0.95rem] leading-relaxed shadow-sm ${isUser
                ? "bg-indigo-600 text-white rounded-br-sm shadow-md"
                : "bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border border-slate-200/50 dark:border-slate-800/50 text-slate-800 dark:text-slate-200 rounded-bl-sm shadow-sm"
                }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-current/10 flex flex-wrap gap-2">
                  {msg.citations.map((cite, idx) => (
                    <div key={idx} className="inline-flex items-center px-2 py-1 rounded-md bg-black/5 dark:bg-white/5 text-[11px] font-medium opacity-90 border border-current/10 backdrop-blur-sm">
                      <FileText className="w-3 h-3 mr-1.5 opacity-70" />
                      {String(cite.source)}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {isUser && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 flex items-center justify-center border border-slate-300/50 dark:border-slate-700/50 shadow-sm hidden sm:flex">
                <User className="w-4 h-4 text-slate-600 dark:text-slate-300" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
