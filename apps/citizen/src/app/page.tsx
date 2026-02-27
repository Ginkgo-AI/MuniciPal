import Link from "next/link";
import Image from "next/image";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col lg:flex-row items-center justify-center p-8 lg:p-16 bg-gradient-to-br from-indigo-50/50 via-white to-slate-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 relative overflow-hidden">

      {/* Text Content */}
      <div className="flex-1 max-w-2xl z-10 text-left transition-all duration-700 animate-in fade-in slide-in-from-bottom-4 mt-12 lg:mt-0">
        <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary mb-6 backdrop-blur-sm">
          Welcome to the Star City
        </div>
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-300">
          Roanoke, VA <br /> <span className="text-primary">Munici-Pal</span>
        </h1>
        <p className="text-xl md:text-2xl text-muted-foreground mb-10 font-light leading-relaxed max-w-xl">
          Your modern AI-powered assistant for the City of Roanoke. Get help with permits,
          FOIA requests, service tickets, and explore the Blue Ridge.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link
            href="/chat"
            className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground px-8 py-3.5 text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/30 hover:-translate-y-0.5 transition-all duration-200 active:scale-[0.98]"
          >
            Start a Conversation
          </Link>
          <Link
            href="/intake"
            className="inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground px-8 py-3.5 text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/30 hover:-translate-y-0.5 transition-all duration-200 active:scale-[0.98]"
          >
            Browse City Services
          </Link>
        </div>
      </div>

      {/* Featured Graphic */}
      <div className="flex-auto w-full max-w-lg mt-16 lg:mt-0 z-10 transition-all duration-1000 delay-300 animate-in fade-in zoom-in-95 lg:ml-12">
        <div className="relative w-full aspect-square rounded-[2.5rem] overflow-hidden shadow-2xl shadow-indigo-900/20 border border-white/20 dark:border-white/5 ring-1 ring-black/5 dark:ring-white/10 group">
          <Image
            src="/roanoke-bg.png"
            alt="Stunning Roanoke Graphic"
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900/40 via-transparent to-transparent opacity-60"></div>
        </div>
      </div>

      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 blur-[100px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-slate-500/10 dark:bg-slate-500/20 blur-[100px]" />
      </div>
    </main>
  );
}
