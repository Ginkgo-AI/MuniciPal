import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          Munici-Pal
        </h1>
        <p className="text-lg text-[var(--muted-foreground)] mb-8">
          Your AI-powered municipal services assistant. Get help with permits,
          FOIA requests, service tickets, and more.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/chat"
            className="inline-flex items-center justify-center rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] px-6 py-3 text-sm font-medium shadow hover:opacity-90 transition"
          >
            Start a Conversation
          </Link>
          <Link
            href="/intake"
            className="inline-flex items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] px-6 py-3 text-sm font-medium shadow-sm hover:bg-[var(--accent)] transition"
          >
            Browse Services
          </Link>
        </div>
      </div>
    </main>
  );
}
