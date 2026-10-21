import { useEffect, useState } from "react";
import { Menu, Moon, Sun, X } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { c3Api } from "@/features/c3-aop-bcs/services/api";

type Theme = "light" | "dark";
type BackendState = "connecting" | "connected" | "unavailable";

function initialTheme(): Theme {
  try { return localStorage.getItem("plantaox-theme") === "dark" ? "dark" : "light"; } catch { return "light"; }
}

export function Header({ mobileNavOpen, onToggleMobileNav }: { mobileNavOpen: boolean; onToggleMobileNav: () => void }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [backend, setBackend] = useState<BackendState>("connecting");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("plantaox-theme", theme); } catch { /* storage can be unavailable */ }
  }, [theme]);
  useEffect(() => {
    let active = true;
    c3Api.health().then(() => { if (active) setBackend("connected"); }, () => { if (active) setBackend("unavailable"); });
    return () => { active = false; };
  }, []);
  return (
    <header className="flex h-16 items-center justify-between border-b px-4 md:px-6" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
      <div className="flex items-center gap-2">
        <button type="button" aria-label={mobileNavOpen ? "Close navigation" : "Open navigation"} aria-expanded={mobileNavOpen} onClick={onToggleMobileNav} className="rounded-lg border p-2 md:hidden" style={{ borderColor: "var(--color-border)" }}>
          {mobileNavOpen ? <X size={16} /> : <Menu size={16} />}
        </button>
        <h1 className="text-lg font-semibold">PlantAOx-RAISE</h1>
      </div>
      <div className="flex items-center gap-2">
        <Badge tone={backend === "connected" ? "success" : backend === "unavailable" ? "danger" : "warning"}>
          Backend {backend}
        </Badge>
        <button type="button" aria-label="Toggle color theme" onClick={() => setTheme((value) => value === "light" ? "dark" : "light")} className="rounded-lg border p-2" style={{ borderColor: "var(--color-border)" }}>
          {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
        </button>
      </div>
    </header>
  );
}
