import { useEffect, useState } from "react";
import { Menu, Moon, Sun, X } from "lucide-react";

type Theme = "light" | "dark";

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem("plantaox-theme");
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // localStorage unavailable (private browsing, etc.) -- fall through
  }
  // Default to light regardless of OS preference -- an explicit choice,
  // not an oversight: the user can still switch to dark via the toggle,
  // which persists their choice in localStorage from then on.
  return "light";
}

export function Header({
  title,
  onToggleMobileNav,
  mobileNavOpen,
}: {
  title: string;
  onToggleMobileNav: () => void;
  mobileNavOpen: boolean;
}) {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("plantaox-theme", theme);
    } catch {
      // ignore persistence failures
    }
  }, [theme]);

  return (
    <header
      className="flex h-16 items-center justify-between border-b px-4 md:px-6"
      style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
    >
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label={mobileNavOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileNavOpen}
          onClick={onToggleMobileNav}
          className="rounded-lg border p-2 md:hidden"
          style={{ borderColor: "var(--color-border)" }}
        >
          {mobileNavOpen ? <X size={16} /> : <Menu size={16} />}
        </button>
        <h1 className="text-lg font-semibold">{title}</h1>
      </div>
      <button
        type="button"
        aria-label="Toggle color theme"
        onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
        className="rounded-lg border p-2"
        style={{ borderColor: "var(--color-border)" }}
      >
        {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
      </button>
    </header>
  );
}
