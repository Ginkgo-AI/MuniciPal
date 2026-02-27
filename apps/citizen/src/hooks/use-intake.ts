"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface WizardDefinition {
  id: string;
  title: string;
  description: string;
  steps: Array<Record<string, unknown>>;
  classification: string;
}

export function useWizards() {
  return useQuery<WizardDefinition[]>({
    queryKey: ["wizards"],
    queryFn: () => apiFetch("/intake/wizards"),
  });
}
