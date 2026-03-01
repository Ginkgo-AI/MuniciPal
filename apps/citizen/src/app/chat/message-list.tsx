"use client";

import { useEffect, useState, useRef } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useSession, useCreateSession, useSendMessage } from "@/hooks/use-chat";
import { Sparkles, FileText, User, Building2 } from "lucide-react";
import { Card, CardContent, cn } from "@municipal/ui";

interface StreamingState {
  isStreaming: boolean;
  content: string;
  citations: Array<Record<string, unknown>>;
  confidence: number | null;
  low_confidence: boolean | null;
}

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
  const [error, setError] = useState<string | null>(null);
  const [streamingState, setStreamingState] = useState<StreamingState | null>(null);
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const { data: session } = useSession(sessionId);
  const createSession = useCreateSession();
  const sendMessage = useSendMessage();
  const t = useTranslations("chat");
  const tCommon = useTranslations("common");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isLoading = createSession.isPending || sendMessage.isPending;

  useEffect(() => {
    const handler = (e: Event) => setSessionId((e as CustomEvent).detail);
    window.addEventListener("municipal:session", handler);
    return () => window.removeEventListener("municipal:session", handler);
  }, []);

  // Listen for streaming updates from ChatInput
  useEffect(() => {
    const handleStreaming = (e: Event) => {
      const detail = (e as CustomEvent).detail as StreamingState;
      setStreamingState(detail);
      if (!detail.isStreaming && !detail.content) {
        // Stream ended and session poll will pick up the message
        setPendingUserMessage(null);
      }
    };
    const handleUserMessage = (e: Event) => {
      setPendingUserMessage((e as CustomEvent).detail as string);
    };
    window.addEventListener("municipal:streaming", handleStreaming);
    window.addEventListener("municipal:user-message", handleUserMessage);
    return () => {
      window.removeEventListener("municipal:streaming", handleStreaming);
      window.removeEventListener("municipal:user-message", handleUserMessage);
    };
  }, []);

  // Auto-scroll when streaming content updates
  useEffect(() => {
    if (streamingState?.isStreaming || streamingState?.content) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [streamingState?.content, streamingState?.isStreaming]);

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
      setError("The response is taking longer than expected. Please wait a moment — it should appear shortly.");
      setTimeout(() => setError(null), 10_000);
    }
  };

  const messages = session?.messages ?? [];

  // Clear pending user message once the session includes it
  useEffect(() => {
    if (pendingUserMessage && messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.role === "assistant" || (lastMsg?.role === "user" && lastMsg.content === pendingUserMessage)) {
        setPendingUserMessage(null);
        setStreamingState(null);
      }
    }
  }, [messages, pendingUserMessage]);

  if (messages.length === 0 && !pendingUserMessage) {
    return (
      <div className="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col justify-center w-full animate-in fade-in zoom-in-95 duration-500 max-w-4xl mx-auto items-center">
        {error && (
          <p className="text-sm font-medium text-destructive mb-4 text-center bg-destructive/10 py-1.5 rounded-md px-3">{error}</p>
        )}

        <div className="w-full relative h-[240px] md:h-[280px] rounded-[2rem] overflow-hidden shadow-2xl shadow-primary/10 mb-8 border border-border/50 shrink-0">
          <Image
            src="/images/roanoke_hero.png"
            alt="MuniciPal Cityscape"
            fill
            className="object-cover"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
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
                onClick={() => !isLoading && handleSuggestedAction(action.prompt)}
                className={cn(
                  "group cursor-pointer hover:border-primary/30 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 enabled:active:scale-[0.98] outline-none focus-visible:ring-2 focus-visible:ring-ring bg-background/60 dark:bg-card/40 border-border/40",
                  isLoading && "pointer-events-none opacity-50"
                )}
                role="button"
                tabIndex={isLoading ? -1 : 0}
                onKeyDown={(e: React.KeyboardEvent<HTMLDivElement>) => {
                  if (!isLoading && (e.key === 'Enter' || e.key === ' ')) {
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
                    <h3 className="font-semibold text-[0.85rem] leading-tight text-foreground group-hover:text-primary transition-colors duration-200 break-words">{t(`services.${action.id}`)}</h3>
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

  // Determine if we should show a streaming bubble
  const showStreamingBubble = streamingState && (streamingState.isStreaming || streamingState.content) && !messages.some(
    (m) => m.role === "assistant" && m.content === streamingState.content
  );

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
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 shadow-sm hidden sm:flex">
                <Building2 className="w-4 h-4 text-primary" />
              </div>
            )}

            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-[20px] px-5 py-3.5 text-[0.95rem] leading-relaxed shadow-sm ${isUser
                ? "bg-primary text-primary-foreground rounded-br-sm shadow-md"
                : "bg-card/80 backdrop-blur-md border border-border/50 text-foreground rounded-bl-sm shadow-sm"
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
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center border border-border shadow-sm hidden sm:flex">
                <User className="w-4 h-4 text-secondary-foreground" />
              </div>
            )}
          </div>
        );
      })}

      {/* Show pending user message while streaming */}
      {pendingUserMessage && !messages.some((m) => m.role === "user" && m.content === pendingUserMessage) && (
        <div className="flex items-end gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300 justify-end">
          <div className="max-w-[85%] sm:max-w-[75%] rounded-[20px] px-5 py-3.5 text-[0.95rem] leading-relaxed shadow-md bg-primary text-primary-foreground rounded-br-sm">
            <p className="whitespace-pre-wrap">{pendingUserMessage}</p>
          </div>
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center border border-border shadow-sm hidden sm:flex">
            <User className="w-4 h-4 text-secondary-foreground" />
          </div>
        </div>
      )}

      {/* Streaming assistant message */}
      {showStreamingBubble && (
        <div className="flex items-end gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300 justify-start">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 shadow-sm hidden sm:flex">
            <Building2 className="w-4 h-4 text-primary" />
          </div>
          <div className="max-w-[85%] sm:max-w-[75%] rounded-[20px] px-5 py-3.5 text-[0.95rem] leading-relaxed shadow-sm bg-card/80 backdrop-blur-md border border-border/50 text-foreground rounded-bl-sm">
            <p className="whitespace-pre-wrap">
              {streamingState.content}
              {streamingState.isStreaming && (
                <span className="inline-block w-2 h-4 bg-primary/60 ml-0.5 animate-pulse rounded-sm" />
              )}
            </p>

            {/* Show citations once streaming is complete */}
            {!streamingState.isStreaming && streamingState.citations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-current/10 flex flex-wrap gap-2 animate-in fade-in duration-500">
                {streamingState.citations.map((cite, idx) => (
                  <div key={idx} className="inline-flex items-center px-2 py-1 rounded-md bg-black/5 dark:bg-white/5 text-[11px] font-medium opacity-90 border border-current/10 backdrop-blur-sm">
                    <FileText className="w-3 h-3 mr-1.5 opacity-70" />
                    {String(cite.source)}
                  </div>
                ))}
              </div>
            )}

            {/* Show confidence once streaming is complete */}
            {!streamingState.isStreaming && streamingState.confidence !== null && (
              <div className="mt-2 animate-in fade-in duration-500">
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${streamingState.confidence >= 0.7
                          ? "bg-green-500"
                          : streamingState.confidence >= 0.5
                            ? "bg-yellow-500"
                            : "bg-red-500"
                        }`}
                      style={{ width: `${Math.round(streamingState.confidence * 100)}%` }}
                    />
                  </div>
                  <span>{Math.round(streamingState.confidence * 100)}% confidence</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}

