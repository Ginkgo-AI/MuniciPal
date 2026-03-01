"use client";

import { useTranslations } from "next-intl";
import { Menu, Settings } from "lucide-react";

interface ChatHeaderProps {
  onToggleSidebar: () => void;
  onOpenModelSettings: () => void;
  currentModel?: string;
}

export function ChatHeader({
  onToggleSidebar,
  onOpenModelSettings,
  currentModel,
}: ChatHeaderProps) {
  const t = useTranslations("chat");

  return (
    <header className="border-b border-[var(--border)] p-4 flex items-center gap-3 bg-[var(--background)]/80 backdrop-blur-md z-20 shrink-0">
      <button
        onClick={onToggleSidebar}
        className="w-9 h-9 rounded-xl flex items-center justify-center text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)] transition-all duration-150 active:scale-95"
        aria-label="Toggle sidebar"
      >
        <Menu className="w-5 h-5" />
      </button>

      <div className="flex-1 min-w-0">
        <h1 className="text-lg font-semibold truncate">{t("title")}</h1>
        <p className="text-xs text-[var(--muted-foreground)] truncate">
          {t("subtitle")}
        </p>
      </div>

      {/* Model Indicator */}
      <button
        onClick={onOpenModelSettings}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs
          bg-[var(--card)] border border-[var(--border)]
          hover:border-[var(--primary)]/30 hover:shadow-sm
          transition-all duration-150 active:scale-95
          text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      >
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        <span className="font-medium max-w-[120px] truncate">
          {currentModel || "No model"}
        </span>
        <Settings className="w-3.5 h-3.5" />
      </button>
    </header>
  );
}
