import Link from "next/link";

export default function StaffHomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gradient-to-br from-indigo-50/50 via-white to-slate-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <div className="max-w-2xl text-center z-10 transition-all duration-700 animate-in fade-in slide-in-from-bottom-4">
        <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary mb-6 backdrop-blur-sm">
          Staff Dashboard
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-300">
          Mission Control
        </h1>
        <p className="text-xl text-muted-foreground mb-10 font-light leading-relaxed">
          Manage operations, monitor sessions, and configure rules for Munici-Pal AI assistants.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground px-8 py-3.5 text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/30 hover:-translate-y-0.5 transition-all duration-200 active:scale-[0.98]"
          >
            Open Dashboard
          </Link>
          <Link
            href="/sessions"
            className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground px-8 py-3.5 text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/30 hover:-translate-y-0.5 transition-all duration-200 active:scale-[0.98]"
          >
            View Sessions
          </Link>
        </div>
      </div>

      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-500/5 dark:bg-indigo-500/10 blur-[100px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-slate-500/5 dark:bg-slate-500/10 blur-[100px]" />
      </div>
    </main>
  );
}
