import { Providers } from "@/lib/providers";
import { IntakeHeader } from "./intake-header";
import { WizardCard } from "./wizard-card";

export default function IntakePage() {
  return (
    <Providers>
      <div className="max-w-4xl mx-auto p-8">
        <IntakeHeader />
        <WizardCard />
      </div>
    </Providers>
  );
}
