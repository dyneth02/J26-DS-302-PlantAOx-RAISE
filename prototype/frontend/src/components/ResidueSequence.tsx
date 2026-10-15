const HYDROPHOBIC = new Set("AILMFWVY".split(""));
const POSITIVE = new Set("KRH".split(""));
const NEGATIVE = new Set("DE".split(""));

function residueColor(ch: string): string {
  const c = ch.toUpperCase();
  if (POSITIVE.has(c)) return "rgb(var(--c-teal))";
  if (NEGATIVE.has(c)) return "rgb(var(--c-coral))";
  if (HYDROPHOBIC.has(c)) return "rgb(var(--c-amber))";
  return "rgb(var(--c-ink-faint))";
}

// Simple residue-level coloring by class (hydrophobic / positively charged / negatively
// charged / polar-neutral) -- not a numeric hydrophobicity gradient, just a legend-based
// classification, cheap to compute client-side from the sequence alone.
export default function ResidueSequence({ sequence }: { sequence: string }) {
  return (
    <div>
      <p className="font-data text-base leading-relaxed">
        {sequence.split("").map((ch, i) => (
          <span key={i} style={{ color: residueColor(ch) }} title={ch}>
            {ch}
          </span>
        ))}
      </p>
      <div className="mt-2 flex flex-wrap gap-3 text-[0.65rem] text-ink-faint">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: "rgb(var(--c-teal))" }} /> positive (K/R/H)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: "rgb(var(--c-coral))" }} /> negative (D/E)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: "rgb(var(--c-amber))" }} /> hydrophobic
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-ink-faint" /> polar / neutral
        </span>
      </div>
    </div>
  );
}
