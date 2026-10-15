import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Search, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export interface SelectOption {
  value: string;
  label: string;
  sublabel?: string;
}

// Searchable combobox -- a plain <select> doesn't scale past a handful of options
// (C1's query picker has 781, C3's browse-picker has 250), so this is type-to-filter
// with a dropdown list, not a native <select>.
export default function Select({
  options,
  value,
  onChange,
  placeholder = "Search…",
  emptyLabel = "No matches",
}: {
  options: SelectOption[];
  value: string | null;
  onChange: (value: string) => void;
  placeholder?: string;
  emptyLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = useMemo(() => options.find((o) => o.value === value) ?? null, [options, value]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options.slice(0, 60);
    return options
      .filter((o) => o.label.toLowerCase().includes(q) || o.sublabel?.toLowerCase().includes(q))
      .slice(0, 60);
  }, [options, query]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, []);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 rounded-lg border border-line-strong bg-surface2 px-3 py-2 text-left text-sm text-ink transition-colors hover:border-lime/40"
      >
        <span className="truncate font-data">
          {selected ? selected.label : <span className="text-ink-faint">{placeholder}</span>}
        </span>
        <ChevronDown size={14} className={`shrink-0 text-ink-faint transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="panel absolute z-40 mt-2 w-full min-w-[16rem] overflow-hidden p-0"
          >
            <div className="flex items-center gap-2 border-b border-line px-3 py-2">
              <Search size={13} className="shrink-0 text-ink-faint" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type to filter…"
                className="w-full bg-transparent text-sm text-ink placeholder:text-ink-faint focus:outline-none font-data"
              />
              {query && (
                <button onClick={() => setQuery("")} className="shrink-0 text-ink-faint hover:text-ink">
                  <X size={13} />
                </button>
              )}
            </div>
            <div className="max-h-64 overflow-y-auto py-1">
              {filtered.length === 0 && (
                <p className="px-3 py-3 text-xs text-ink-faint">{emptyLabel}</p>
              )}
              {filtered.map((o) => (
                <button
                  key={o.value}
                  onClick={() => {
                    onChange(o.value);
                    setOpen(false);
                    setQuery("");
                  }}
                  className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-lime/[0.06] ${
                    o.value === value ? "bg-lime/[0.08] text-lime" : "text-ink"
                  }`}
                >
                  <span className="truncate font-data">{o.label}</span>
                  {o.sublabel && <span className="label-tag shrink-0 text-ink-faint">{o.sublabel}</span>}
                </button>
              ))}
              {options.length > filtered.length && filtered.length === 60 && (
                <p className="px-3 py-2 text-[0.65rem] text-ink-faint">Showing first 60 matches — keep typing to narrow down.</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
