import { useState, type ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen" style={{ background: "var(--color-bg)" }}>
      <Sidebar className="hidden md:flex" />

      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            aria-label="Close navigation overlay"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileNavOpen(false)}
          />
          <Sidebar className="relative z-10 h-full shadow-lg" onNavigate={() => setMobileNavOpen(false)} />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          title={title}
          mobileNavOpen={mobileNavOpen}
          onToggleMobileNav={() => setMobileNavOpen((open) => !open)}
        />
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-6">
          <div className="mx-auto max-w-6xl space-y-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
