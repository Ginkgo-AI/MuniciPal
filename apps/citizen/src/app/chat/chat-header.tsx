"use client";

import { useTranslations } from "next-intl";

export function ChatHeader() {
  const t = useTranslations("chat");

  return (
    <header className="border-b border-[var(--border)] p-4">
      <h1 className="text-lg font-semibold">{t("title")}</h1>
      <p className="text-sm text-[var(--muted-foreground)]">{t("subtitle")}</p>
    </header>
  );
}
