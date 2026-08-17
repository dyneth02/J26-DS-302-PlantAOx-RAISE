/** @type {import('tailwindcss').Config} */

// Reads a "R G B" CSS custom property (set per-theme in index.css) and lets Tailwind's
// opacity modifiers (bg-lime/10, text-teal/70, ...) work against it.
function withOpacity(variable) {
  return ({ opacityValue }) =>
    opacityValue === undefined ? `rgb(var(${variable}))` : `rgb(var(${variable}) / ${opacityValue})`;
}

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
        sans: ["Manrope", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        void: withOpacity("--c-void"),
        surface: withOpacity("--c-surface"),
        surface2: withOpacity("--c-surface2"),
        surface3: withOpacity("--c-surface3"),
        ink: withOpacity("--c-ink"),
        "ink-dim": withOpacity("--c-ink-dim"),
        "ink-faint": withOpacity("--c-ink-faint"),
        line: "var(--c-line)",
        "line-strong": "var(--c-line-strong)",
        lime: withOpacity("--c-lime"),
        teal: withOpacity("--c-teal"),
        violet: withOpacity("--c-violet"),
        amber: withOpacity("--c-amber"),
        coral: withOpacity("--c-coral"),
        tier1: withOpacity("--c-teal"),
        tier2: withOpacity("--c-amber"),
        tierdual: withOpacity("--c-violet"),
        tier3: withOpacity("--c-ink-faint"),
      },
      boxShadow: {
        glow: "0 0 40px -8px rgb(var(--c-lime) / 0.3)",
        "glow-teal": "0 0 40px -8px rgb(var(--c-teal) / 0.3)",
        card: "0 1px 0 0 rgb(var(--c-ink) / 0.04) inset, 0 20px 40px -24px rgba(0,0,0,0.45)",
      },
      keyframes: {
        drift: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(3%, -4%) scale(1.05)" },
        },
        pulse2: {
          "0%, 100%": { opacity: 0.6 },
          "50%": { opacity: 1 },
        },
      },
      animation: {
        drift: "drift 18s ease-in-out infinite",
        drift2: "drift 24s ease-in-out infinite reverse",
        pulse2: "pulse2 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
