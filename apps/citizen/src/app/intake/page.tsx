import { Providers } from "@/lib/providers";
import { WizardCard } from "./wizard-card";

export default function IntakePage() {
  return (
    <Providers>
      <div className="max-w-4xl mx-auto p-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">City Services</h1>
          <p className="text-[var(--muted-foreground)] mt-2">
            Browse available services and start an application
          </p>
        </header>
        <WizardCard />
      </div>
    </Providers>
  );
}
