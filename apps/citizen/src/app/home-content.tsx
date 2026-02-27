"use client";

import Link from "next/link";
import Image from "next/image";
import { useTranslations } from "next-intl";

export function HomeContent() {
  const t = useTranslations("home");

  return (
    <main className="flex min-h-screen flex-col lg:flex-row items-center justify-center p-8 lg:p-16 bg-gradient-to-br from-indigo-50/60 via-white to-slate-50/80 dark:from-slate-950 dark:via-[#020617] dark:to-slate-950 relative overflow-hidden">

      {/* Text Content */}
      <div className="flex-1 max-w-2xl z-10 text-left animate-fade-in-up mt-12 lg:mt-0">
        <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-semibold text-primary mb-6 backdrop-blur-sm">
          {t("badge")}
        </div>
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-slate-700 to-slate-500 dark:from-white dark:via-slate-200 dark:to-slate-400">
          {t("heading")} <br /> <span className="bg-gradient-to-r from-indigo-600 to-violet-500 dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">{t("brand")}</span>
        </h1>
        <p className="text-lg md:text-xl text-muted-foreground mb-10 font-light leading-relaxed max-w-xl">
          {t("description")}
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link
            href="/chat"
            className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground px-8 py-3.5 text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 transition-all duration-200 enabled:active:scale-[0.97]"
          >
            {t("startChat")}
          </Link>
          <Link
            href="/intake"
            className="inline-flex items-center justify-center rounded-full border border-border bg-background/80 backdrop-blur-sm text-foreground px-8 py-3.5 text-sm font-semibold shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 enabled:active:scale-[0.97]"
          >
            {t("browseServices")}
          </Link>
        </div>
      </div>

      {/* Featured Graphic */}
      <div className="flex-auto w-full max-w-lg mt-16 lg:mt-0 z-10 animate-fade-in-up lg:ml-12" style={{ animationDelay: "0.15s" }}>
        <div className="relative w-full aspect-square rounded-[2.5rem] overflow-hidden shadow-2xl shadow-indigo-900/15 dark:shadow-indigo-500/10 border border-white/20 dark:border-white/5 ring-1 ring-black/5 dark:ring-white/10 group">
          <Image
            src="/roanoke-bg.png"
            alt="Stunning Roanoke Graphic"
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900/40 via-transparent to-transparent opacity-60"></div>
        </div>
      </div>

      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-15%] left-[-10%] w-[45%] h-[45%] rounded-full bg-indigo-400/8 dark:bg-indigo-500/15 blur-[120px]" />
        <div className="absolute bottom-[-15%] right-[-10%] w-[45%] h-[45%] rounded-full bg-violet-400/6 dark:bg-violet-500/10 blur-[120px]" />
        <div className="absolute top-[40%] right-[20%] w-[25%] h-[25%] rounded-full bg-slate-400/5 dark:bg-slate-500/10 blur-[100px]" />
      </div>
    </main>
  );
}
