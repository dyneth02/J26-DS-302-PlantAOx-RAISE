import { NavLink, Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useTheme } from "../hooks/useTheme";

const NAV_ITEMS = [
  { to: "/", label: "Home", tag: "00", end: true },
  { to: "/c1", label: "AOP-ProCon", tag: "C1", end: false },
  { to: "/c2", label: "PU-AOP", tag: "C2", end: false },
  { to: "/c3", label: "AOP-BCS", tag: "C3", end: false },
  { to: "/c4", label: "PlantAOP-Screen", tag: "C4", end: false },
];

function Mark() {
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none" className="shrink-0">
      <polygon
        points="17,2 30,9.5 30,24.5 17,32 4,24.5 4,9.5"
        stroke="rgb(var(--c-lime))"
        strokeWidth="1.4"
        fill="rgb(var(--c-lime) / 0.06)"
      />
      <path d="M17 9 C 12 12, 12 18, 17 25 C 22 18, 22 12, 17 9 Z" fill="rgb(var(--c-teal))" opacity="0.85" />
      <circle cx="17" cy="17" r="1.6" fill="rgb(var(--c-void))" />
    </svg>
  );
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isLight = theme === "light";
  return (
    <button
      onClick={toggle}
      aria-label="Toggle color theme"
      className="group relative flex h-8 w-14 shrink-0 items-center rounded-full border border-line-strong bg-surface2 px-1 transition-colors hover:border-lime/40"
    >
      <motion.span
        layout
        transition={{ type: "spring", stiffness: 500, damping: 32 }}
        className="flex h-6 w-6 items-center justify-center rounded-full bg-void shadow-sm"
        style={{ marginLeft: isLight ? "auto" : 0 }}
      >
        {isLight ? (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="4.2" stroke="rgb(var(--c-amber))" strokeWidth="2" />
            <g stroke="rgb(var(--c-amber))" strokeWidth="2" strokeLinecap="round">
              <path d="M12 2v2.2M12 19.8V22M4.2 4.2l1.6 1.6M18.2 18.2l1.6 1.6M2 12h2.2M19.8 12H22M4.2 19.8l1.6-1.6M18.2 5.8l1.6-1.6" />
            </g>
          </svg>
        ) : (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
            <path
              d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"
              fill="rgb(var(--c-lime))"
            />
          </svg>
        )}
      </motion.span>
    </button>
  );
}

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen flex">
      <div className="fixed right-6 top-6 z-50">
        <ThemeToggle />
      </div>

      <aside className="w-72 shrink-0 border-r border-line bg-surface/60 backdrop-blur-sm px-6 py-8 flex flex-col">
        <div className="flex items-center gap-3">
          <Mark />
          <div>
            <p className="font-display text-xl leading-none tracking-tight text-ink">
              PlantAOx<span className="text-lime">·</span>RAISE
            </p>
            <p className="label-tag mt-1.5 text-ink-faint">Proposal Prototype</p>
          </div>
        </div>

        <div className="mt-10 h-px w-full bg-gradient-to-r from-line-strong via-line to-transparent" />

        <nav className="mt-8 flex flex-col gap-1">
          {NAV_ITEMS.map(({ to, label, tag, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
                  isActive ? "text-ink" : "text-ink-dim hover:text-ink"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-lg bg-lime/[0.08] ring-1 ring-lime/25"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  <span
                    className={`label-tag relative z-10 flex h-6 w-8 shrink-0 items-center justify-center rounded border ${
                      isActive ? "border-lime/40 text-lime" : "border-line-strong text-ink-faint group-hover:border-line-strong"
                    }`}
                  >
                    {tag}
                  </span>
                  <span className="relative z-10 font-medium text-[0.925rem]">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto pt-8">
          <div className="panel px-4 py-3.5">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-lime opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-lime" />
              </span>
              <p className="label-tag text-ink-dim">Live artifacts</p>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-faint">
              Every number on this dashboard is read from real, generated data — nothing is hardcoded.
            </p>
          </div>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
