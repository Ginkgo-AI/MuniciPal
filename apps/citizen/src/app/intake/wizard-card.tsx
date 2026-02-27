"use client";

import { useTranslations } from "next-intl";
import { useWizards } from "@/hooks/use-intake";

export function WizardCard() {
  const { data: wizards, isLoading, error } = useWizards();
  const t = useTranslations("intake");
  const tCommon = useTranslations("common");

  if (isLoading) {
    return <p className="text-[var(--muted-foreground)]">{tCommon("loading")}</p>;
  }

  if (error) {
    return (
      <p className="text-[var(--destructive)]">{t("loadError")}</p>
    );
  }

  if (!wizards || wizards.length === 0) {
    return <p className="text-[var(--muted-foreground)]">{t("noServices")}</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {wizards.map((wizard) => (
        <div
          key={wizard.id}
          className="rounded-2xl border border-[var(--border)]/60 bg-[var(--card)]/95 p-6 shadow-sm shadow-black/[0.03] backdrop-blur-sm hover:shadow-lg hover:shadow-black/[0.06] transition-all duration-300"
        >
          <h2 className="font-semibold text-lg mb-2">{wizard.title}</h2>
          <p className="text-sm text-[var(--muted-foreground)] mb-4">
            {wizard.description}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--muted-foreground)]">
              {t("steps", { count: wizard.steps.length })}
            </span>
            <span className="text-xs px-2 py-1 rounded-full bg-[var(--secondary)] text-[var(--secondary-foreground)]">
              {wizard.classification}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
