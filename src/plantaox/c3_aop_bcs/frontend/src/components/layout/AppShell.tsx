import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  return (
    <div className="flex h-screen" style={{ background: "var(--color-bg)" }}>
      <Sidebar className="hidden md:flex" />
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button type="button" aria-label="Close navigation overlay" className="absolute inset-0 bg-black/40" onClick={() => setMobileNavOpen(false)} />
          <Sidebar className="relative z-10 h-full shadow-lg" onNavigate={() => setMobileNavOpen(false)} />
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <Header mobileNavOpen={mobileNavOpen} onToggleMobileNav={() => setMobileNavOpen((open) => !open)} />
        <main id="main-content" className="flex-1 overflow-y-auto px-4 py-6 md:px-6" tabIndex={-1}>
          <div className="mx-auto max-w-6xl space-y-6"><Outlet /></div>
        </main>
      </div>
    </div>
  );
}
