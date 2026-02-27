import Link from "next/link";

export default function StaffHomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight mb-2">
          Mission Control
        </h1>
        <p className="text-sm text-[var(--muted-foreground)] mb-6">
          Munici-Pal Staff Dashboard
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] px-6 py-3 text-sm font-medium shadow hover:opacity-90 transition"
          >
            Dashboard
          </Link>
          <Link
            href="/sessions"
            className="inline-flex items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] px-6 py-3 text-sm font-medium shadow-sm hover:bg-[var(--accent)] transition"
          >
            Sessions
          </Link>
        </div>
      </div>
    </main>
  );
}
