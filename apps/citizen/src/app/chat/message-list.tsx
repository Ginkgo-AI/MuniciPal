"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useSession, useCreateSession, useSendMessage } from "@/hooks/use-chat";
import { Sparkles, FileText, User, Building2 } from "lucide-react";
import { Card, CardContent } from "@municipal/ui";

const GRID_SERVICES = [
  { id: "reportIssue", imgSrc: "/images/icon_report_issue.png", prompt: "I need to report an issue." },
  { id: "permits", imgSrc: "/images/icon_permits.png", prompt: "I need help with a permit or license." },
  { id: "exploreParks", imgSrc: "/images/icon_explore_parks.png", prompt: "Tell me about local parks and recreation." },
  { id: "payBill", imgSrc: "/images/icon_pay_bill.png", prompt: "How do I pay my utility bill?" },
  { id: "publicRecords", imgSrc: "/images/icon_public_records.png", prompt: "I want to submit a FOIA public records request." },
  { id: "voting", imgSrc: "/images/icon_voting.png", prompt: "How do I register to vote?" },
  { id: "cityCouncil", imgSrc: "/images/icon_city_council.png", prompt: "When is the next city council meeting?" },
  { id: "library", imgSrc: "/images/icon_library.png", prompt: "What are the library hours and services?" },
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
        <div className="w-full relative h-[240px] md:h-[280px] rounded-[2rem] overflow-hidden shadow-2xl shadow-indigo-500/10 mb-8 border border-border/50 shrink-0">
          <Image
            src="/images/roanoke_hero.png"
            alt="MuniciPal Cityscape"
            fill
            className="object-cover"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900/90 via-slate-900/20 to-transparent" />
          <div className="absolute inset-0 flex flex-col items-center justify-end p-6 md:p-8 text-center pb-6 md:pb-8">
            <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-white/10 backdrop-blur-md text-white border border-white/20 mb-3 md:mb-4 shadow-lg ring-1 ring-white/10">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2
              className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-1.5 md:mb-2"
              style={{ textShadow: "0 2px 10px rgba(0,0,0,0.5)" }}
            >
              {t("welcome")}
            </h2>
            <p
              className="text-slate-200 max-w-lg text-xs md:text-sm leading-relaxed"
              style={{ textShadow: "0 1px 5px rgba(0,0,0,0.8)" }}
            >
              {t("welcomeDesc")}
            </p>
          </div>
        </div>

        {/* Apple-style Compact Grid with Shadcn Cards and 3D Assets */}
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
                    <div className="w-10 h-10 relative flex-shrink-0 rounded-xl overflow-hidden shadow-sm border border-border/50 group-hover:shadow-md transition-all duration-200 bg-white">
                      <Image
                        src={action.imgSrc}
                        alt={t(`services.${action.id}`)}
                        fill
                        className="object-cover transition-transform duration-300 group-hover:scale-105"
                      />
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
