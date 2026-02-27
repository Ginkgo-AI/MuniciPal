"use client";

import { useWizards } from "@/hooks/use-intake";

export function WizardCard() {
  const { data: wizards, isLoading, error } = useWizards();

  if (isLoading) {
    return <p className="text-[var(--muted-foreground)]">Loading services...</p>;
  }

  if (error) {
    return (
      <p className="text-[var(--destructive)]">
        Unable to load services. Make sure the backend is running.
      </p>
    );
  }

  if (!wizards || wizards.length === 0) {
    return <p className="text-[var(--muted-foreground)]">No services available.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {wizards.map((wizard) => (
        <div
          key={wizard.id}
          className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-sm hover:shadow-md transition"
        >
          <h2 className="font-semibold text-lg mb-2">{wizard.title}</h2>
          <p className="text-sm text-[var(--muted-foreground)] mb-4">
            {wizard.description}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--muted-foreground)]">
              {wizard.steps.length} steps
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
