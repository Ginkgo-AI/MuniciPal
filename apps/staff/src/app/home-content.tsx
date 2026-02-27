"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

export function HomeContent() {
  const t = useTranslations("home");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gradient-to-br from-teal-50/40 via-white to-slate-50/80 dark:from-slate-950 dark:via-[#020617] dark:to-slate-950 relative overflow-hidden">
      <div className="max-w-2xl text-center z-10 animate-fade-in-up">
        <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-semibold text-primary mb-6 backdrop-blur-sm">
          {t("badge")}
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-slate-700 to-slate-500 dark:from-white dark:via-slate-200 dark:to-slate-400">
          {t("title")}
        </h1>
        <p className="text-lg text-muted-foreground mb-10 font-light leading-relaxed">
          {t("subtitle")}
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground px-8 py-3.5 text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 transition-all duration-200 enabled:active:scale-[0.97]"
          >
            {t("openDashboard")}
          </Link>
          <Link
            href="/sessions"
            className="inline-flex items-center justify-center rounded-full border border-border bg-background/80 backdrop-blur-sm text-foreground px-8 py-3.5 text-sm font-semibold shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 enabled:active:scale-[0.97]"
          >
            {t("viewSessions")}
          </Link>
        </div>
      </div>

      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-15%] right-[-10%] w-[45%] h-[45%] rounded-full bg-teal-400/6 dark:bg-teal-500/10 blur-[120px]" />
        <div className="absolute bottom-[-15%] left-[-10%] w-[45%] h-[45%] rounded-full bg-slate-400/5 dark:bg-slate-500/8 blur-[120px]" />
        <div className="absolute top-[30%] left-[25%] w-[20%] h-[20%] rounded-full bg-emerald-400/4 dark:bg-emerald-500/8 blur-[100px]" />
      </div>
    </main>
  );
}
