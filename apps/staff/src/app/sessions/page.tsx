import { Providers } from "@/lib/providers";
import { SessionTable } from "./session-table";

export default function SessionsPage() {
  return (
    <Providers>
      <div className="max-w-6xl mx-auto p-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Sessions</h1>
          <p className="text-[var(--muted-foreground)] mt-1">
            Active chat sessions
          </p>
        </header>
        <SessionTable />
      </div>
    </Providers>
  );
}
