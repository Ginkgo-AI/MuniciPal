"use client";

import { useTranslations } from "next-intl";

export function IntakeHeader() {
  const t = useTranslations("intake");

  return (
    <header className="mb-8">
      <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
      <p className="text-[var(--muted-foreground)] mt-2">{t("subtitle")}</p>
    </header>
  );
}
