import { useMemo, useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { C1_COLORS, Callout, HBarChart, Legend, ScatterPlot, ScatterPlot3D, Toggle } from "@/features/c1-procon/components/charts";
import type { BarItem, ScatterPoint, ScatterPoint3D } from "@/features/c1-procon/components/charts";
import type { EmbeddingPoint, EmbeddingResponse, EmbeddingSpace } from "@/features/c1-procon/types";

type SpaceKey = "esm2" | "primary" | "maxspread";
type ColorBy = "class" | "length" | "source";
type Dimension = "2d" | "3d";

const CLASS_LABELS = {
  mc: "MC-active (metal chelation)",
  frs: "FRS-only (radical scavenging)",
  other: "not in the strict pool (mechanism not established)",
} as const;

const SPACE_OPTIONS: [SpaceKey, string][] = [
  ["esm2", "Untrained ESM-2"],
  ["primary", "Main trained head"],
  ["maxspread", "Spread-selected head"],
];
const DIMENSION_OPTIONS: [Dimension, string][] = [
  ["2d", "2D map"],
  ["3d", "3D map"],
];
const COLOR_OPTIONS: [ColorBy, string][] = [
  ["class", "Mechanism (MC vs FRS)"],
  ["length", "Peptide length"],
  ["source", "Data source"],
];
const SPACE_STORY: Record<SpaceKey, (s: EmbeddingSpace) => { tone: "info" | "warn" | "bad"; title: string; text: string }> = {
  esm2: () => ({
    tone: "info",
    title: "Untrained ESM-2: structure comes from length, not from mechanism",
    text: "The two big clouds are short and long peptides (the pooling rule changes at 10 amino acids). Metal-chelating peptides (purple) sit inside the radical-scavenging peptides (teal): the frozen embedding does not separate the two mechanisms.",
  }),
  primary: (s) => ({
    tone: "bad",
    title: "Main trained head: everything is pulled to almost the same point",
    text: `Training only had positive pairs to pull together, so the head took the shortcut of putting every peptide close to every other (average cosine ${s.all_pairs.toFixed(3)}). That is embedding collapse: the map shrinks to a thin band and neighbours carry no mechanism information.`,
  }),
  maxspread: (s) => ({
    tone: "warn",
    title: "Spread-selected head: spread out again, but not by mechanism",
    text: `Choosing the checkpoint that keeps the embedding spread avoids collapse (average cosine ${s.all_pairs.toFixed(2)}). MC-active peptides are still mixed with the others, so the neighbours are about as good as a random guess.`,
  }),
};

function classColor(p: EmbeddingPoint): string {
  if (p.strict_class === "MC-active") return C1_COLORS.mc;
  if (p.strict_class === "FRS-only") return C1_COLORS.frs;
  return C1_COLORS.gen;
}
const LENGTH_BINS: [string, string, (n: number) => boolean][] = [
  ["3 aa (tripeptides)", "#f59e0b", (n) => n === 3],
  ["4-5 aa", "#10b981", (n) => n >= 4 && n <= 5],
  ["6-9 aa", "#3b82f6", (n) => n >= 6 && n <= 9],
  ["10+ aa (mean-pooled)", "#ef4444", (n) => n >= 10],
];
function lengthColor(p: EmbeddingPoint): string {
  return LENGTH_BINS.find(([, , test]) => test(p.length))?.[1] ?? C1_COLORS.gen;
}
const SOURCE_PALETTE = ["#0f766e", "#f97316", "#64748b", "#a855f7"];

function PullTogetherIllustration() {
  // Purely illustrative: the GOAL of contrastive learning, not a result.
  const before = [
    [30, 34, "m"], [88, 22, "f"], [60, 62, "m"], [112, 70, "f"], [24, 84, "f"], [96, 100, "m"], [52, 106, "f"], [128, 40, "m"], [70, 38, "f"],
  ] as const;
  const after = [
    [30, 40, "m"], [44, 52, "m"], [36, 66, "m"], [50, 36, "m"], [110, 90, "f"], [124, 100, "f"], [100, 104, "f"], [118, 78, "f"], [136, 92, "f"],
  ] as const;
  const dot = (cx: number, cy: number, kind: string) => (
    <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={6.5} fill={kind === "m" ? C1_COLORS.mc : C1_COLORS.frs} opacity={0.9} />
  );
  return (
    <svg viewBox="0 0 400 140" width="100%" role="img" aria-label="Illustration of contrastive learning: same-mechanism peptides move closer together" style={{ display: "block" }}>
      <g>
        <rect x={4} y={4} width={162} height={132} rx={10} fill="none" stroke="var(--color-border)" />
        {before.map(([x, y, k]) => dot(x, y, k))}
        <text x={85} y={132} fontSize={10} textAnchor="middle" fill="var(--color-text-muted)">before training</text>
      </g>
      <g>
        <path d="M172 70 H226" stroke="var(--color-text-muted)" strokeWidth={2} markerEnd="url(#arrow)" />
        <text x={199} y={60} fontSize={10} textAnchor="middle" fill="var(--color-text-muted)">pull same-</text>
        <text x={199} y={86} fontSize={10} textAnchor="middle" fill="var(--color-text-muted)">mechanism pairs</text>
      </g>
      <g transform="translate(232 0)">
        <rect x={4} y={4} width={162} height={132} rx={10} fill="none" stroke="var(--color-border)" />
        {after.map(([x, y, k]) => dot(x, y, k))}
        <text x={85} y={132} fontSize={10} textAnchor="middle" fill="var(--color-text-muted)">the goal</text>
      </g>
      <defs>
        <marker id="arrow" markerWidth={8} markerHeight={8} refX={6} refY={4} orient="auto">
          <path d="M0 0 L8 4 L0 8 z" fill="var(--color-text-muted)" />
        </marker>
      </defs>
    </svg>
  );
}

function EmbeddingBody({ data }: { data: EmbeddingResponse }) {
  const [space, setSpace] = useState<SpaceKey>("esm2");
  const [colorBy, setColorBy] = useState<ColorBy>("class");
  const [dimension, setDimension] = useState<Dimension>("2d");
  const [hiddenGroups, setHiddenGroups] = useState<ReadonlySet<string>>(new Set());
  const [hovered, setHovered] = useState<string | null>(null);

  const bySequence = useMemo(() => new Map(data.points.map((p) => [p.sequence, p])), [data.points]);
  const sources = useMemo(() => Array.from(new Set(data.points.map((p) => p.source_group ?? "unknown"))).sort(), [data.points]);
  const sourceColor = (name: string) => SOURCE_PALETTE[sources.indexOf(name) % SOURCE_PALETTE.length];

  const groupOf = (p: EmbeddingPoint): string =>
    colorBy === "class"
      ? p.strict_class === "MC-active"
        ? CLASS_LABELS.mc
        : p.strict_class === "FRS-only"
          ? CLASS_LABELS.frs
          : CLASS_LABELS.other
      : colorBy === "length"
        ? (LENGTH_BINS.find(([, , test]) => test(p.length))?.[0] ?? "other")
        : (p.source_group ?? "unknown");
  const toggleGroup = (label: string) =>
    setHiddenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  const changeColorBy = (value: ColorBy) => {
    setColorBy(value);
    setHiddenGroups(new Set()); // the groups differ between colourings
  };

  const points: ScatterPoint[] = data.points.map((p) => {
    const color = colorBy === "class" ? classColor(p) : colorBy === "length" ? lengthColor(p) : sourceColor(p.source_group ?? "unknown");
    return {
      hidden: hiddenGroups.has(groupOf(p)),
      id: p.sequence,
      x: p.coords[space][0],
      y: p.coords[space][1],
      color,
      faint: colorBy === "class" && p.strict_class === "not in strict pool",
      radius: colorBy === "class" && p.strict_class === "MC-active" ? 4.2 : 3.2,
    };
  });

  const points3d: ScatterPoint3D[] = points.map((p, i) => ({ ...p, z: data.points[i].coords[space][2] ?? 0 }));

  const legend: [string, string][] =
    colorBy === "class"
      ? [[C1_COLORS.mc, CLASS_LABELS.mc], [C1_COLORS.frs, CLASS_LABELS.frs], [C1_COLORS.gen, CLASS_LABELS.other]]
      : colorBy === "length"
        ? LENGTH_BINS.map(([label, color]) => [color, label] as [string, string])
        : sources.map((s) => [sourceColor(s), s] as [string, string]);

  const current = data.spaces.find((s) => s.key === space)!;
  const story = SPACE_STORY[space](current);
  const [esm, prim, maxs] = ["esm2", "primary", "maxspread"].map((k) => data.spaces.find((s) => s.key === k)!);
  const hover = hovered ? bySequence.get(hovered) : undefined;
  const xLabel = `PC1 (${(current.pc_variance_share[0] * 100).toFixed(0)}% of the variance)`;
  const yLabel = `PC2 (${(current.pc_variance_share[1] * 100).toFixed(0)}%)`;
  const zShare = current.pc_variance_share[2];
  const zLabel = `PC3 (${zShare === undefined ? "n/a" : (zShare * 100).toFixed(0) + "%"})`;

  const cosineItems: BarItem[] = data.spaces.flatMap((s) => [
    { label: `${s.name} - MC with MC`, value: s.within_mc, color: C1_COLORS.mc },
    { label: `${s.name} - FRS with FRS`, value: s.within_frs, color: C1_COLORS.frs },
    { label: `${s.name} - MC with FRS`, value: s.between, color: C1_COLORS.gen },
  ]);
  const purityItems: BarItem[] = data.spaces.map((s) => ({
    label: s.name,
    value: s.mc_neighbour_purity,
    color: s.mc_neighbour_purity > data.meta.chance_mc_neighbour_purity ? C1_COLORS.baseline : C1_COLORS.bad,
  }));
  const pairItems: BarItem[] = data.pair_counts.map((c) => ({
    label: c.pair_set.replaceAll("_", " "),
    value: c.pairs,
    color: c.pair_set.includes("random") || c.pair_set.includes("physchem") ? C1_COLORS.gen : C1_COLORS.mc,
  }));

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Embeddings and contrastive learning - MC vs FRS"
          subtitle="Can a learned embedding place metal-chelating (MC) peptides apart from radical-scavenging (FRS) peptides?"
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <ol className="space-y-3 text-sm">
            {[
              ["1", "Embed", "ESM-2, a pretrained protein model, turns every peptide into a list of 1,280 numbers (an embedding)."],
              ["2", "Pair", "We tell the model which peptides should be neighbours: pairs of the same mechanism that look alike chemically."],
              ["3", "Train", "A small head (1,280 → 128 numbers) is trained so that paired peptides move closer together."],
              ["4", "Retrieve", "For a query peptide we rank all others by closeness and check whether the top ones share its mechanism."],
            ].map(([n, title, text]) => (
              <li key={n} className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: "var(--color-primary)" }}>
                  {n}
                </span>
                <span>
                  <b>{title}.</b> <span style={{ color: "var(--color-text-muted)" }}>{text}</span>
                </span>
              </li>
            ))}
          </ol>
          <div>
            <PullTogetherIllustration />
            <p className="mt-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
              Illustration of the goal of training. The real result is in the maps below.
            </p>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="What the model is told to pull together" subtitle={`Strict mode training pairs; only positive pairs are used, no confirmed-negative peptides.`} />
        <HBarChart items={pairItems} max={Math.max(...pairItems.map((p) => p.value)) * 1.15} decimals={0} labelWidth={240} ariaLabel="Number of training pairs per pair set" />
        <ul className="mt-3 list-disc space-y-1 pl-5 text-xs" style={{ color: "var(--color-text-muted)" }}>
          {data.pair_counts.map((c) => (
            <li key={c.pair_set}>{c.description}</li>
          ))}
        </ul>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {data.pair_examples.map((e) => (
            <div key={`${e.seq1}-${e.seq2}`} className="rounded-lg border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)" }}>
              <Badge tone={e.mechanism === "MC" ? "accent" : "success"}>{e.mechanism}</Badge>{" "}
              <code>{e.seq1}</code> ↔ <code>{e.seq2}</code>
              <span className="ml-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
                distance {e.distance.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Map of the 1,389 peptides"
          subtitle={`Each dot is a peptide; peptides that look alike to the model sit close together (${dimension === "3d" ? "3-D" : "2-D"} PCA of the embedding).`}
        />
        <div className="mb-3 flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-muted)" }}>Embedding</span>
            <Toggle options={SPACE_OPTIONS} value={space} onChange={setSpace} />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-muted)" }}>View</span>
            <Toggle options={DIMENSION_OPTIONS} value={dimension} onChange={setDimension} />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-muted)" }}>Colour by</span>
            <Toggle options={COLOR_OPTIONS} value={colorBy} onChange={changeColorBy} />
          </div>
        </div>
        {dimension === "2d" ? (
          <ScatterPlot points={points} xLabel={xLabel} yLabel={yLabel} onHover={setHovered} ariaLabel={`PCA map of the peptides in the ${current.name} space`} />
        ) : (
          <ScatterPlot3D
            points={points3d}
            axisLabels={[xLabel, yLabel, zLabel]}
            onHover={setHovered}
            ariaLabel={`3-D PCA map of the peptides in the ${current.name} space`}
          />
        )}
        <Legend entries={legend} hidden={hiddenGroups} onToggle={toggleGroup} />
        <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
          Click a legend entry to hide or show that group.
        </p>
        <p className="mt-2 min-h-5 text-xs" style={{ color: "var(--color-text-muted)" }} aria-live="polite">
          {hover ? (
            <>
              <code>{hover.sequence}</code> · label {hover.label} · {hover.length} aa · source {hover.source_group ?? "unknown"}
            </>
          ) : (
            "Hover over a dot to see the peptide."
          )}
        </p>
        <div className="mt-3">
          <Callout title={story.title} tone={story.tone}>
            {story.text}
          </Callout>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Do MC peptides sit together?"
          subtitle="Average cosine similarity between peptides of the strict pool (1.0 = identical direction). If the mechanism were learned, MC-MC would be clearly higher than MC-FRS."
        />
        <HBarChart items={cosineItems} min={0} max={1} decimals={3} labelWidth={290} ariaLabel="Average cosine similarity within and between mechanism classes" />
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {data.spaces.map((s) => (
            <StatTile
              key={s.key}
              label={`separation, ${s.name}`}
              value={s.separation.toFixed(3)}
              hint="within-class minus between-class cosine"
            />
          ))}
        </div>
        <div className="mt-4">
          <Callout title="In plain words" tone="warn">
            In the untrained embedding the average similarity is {esm.within_mc.toFixed(2)} for MC with MC, {esm.within_frs.toFixed(2)} for FRS with FRS and {esm.between.toFixed(2)} between the two
            classes: the classes are not separated. The main trained head makes every pair almost identical ({prim.all_pairs.toFixed(3)}), and the spread-selected head separates the classes by
            only {maxs.separation.toFixed(3)}.
          </Callout>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Do the nearest neighbours of an MC-active peptide share its mechanism?"
          subtitle={`Share of the ${data.meta.neighbours} nearest neighbours that are MC-active (neighbours from the same homology group are excluded). Random guessing gives ${(data.meta.chance_mc_neighbour_purity * 100).toFixed(1)}%.`}
        />
        <HBarChart
          items={purityItems}
          min={0}
          max={0.25}
          decimals={3}
          labelWidth={230}
          refs={[{ value: data.meta.chance_mc_neighbour_purity, label: `random guess ${data.meta.chance_mc_neighbour_purity.toFixed(3)}` }]}
          ariaLabel="Share of MC-active nearest neighbours per embedding"
        />
        <div className="mt-4">
          <Callout title="Why trained models lose to the untrained embedding in retrieval" tone="bad">
            The untrained embedding finds slightly more MC-active neighbours than chance ({data.spaces[0].mc_neighbour_purity.toFixed(3)}), mostly because length and composition carry a
            little signal. The main trained head falls below chance ({data.spaces[1].mc_neighbour_purity.toFixed(3)}) because it has collapsed. This is the same story as the retrieval
            results: 0 of 25 trained runs beat the untrained embedding.
          </Callout>
        </div>
      </Card>

      <Card>
        <CardHeader title="How to read these maps" />
        <ul className="list-disc space-y-2 pl-5 text-sm">
          {data.reading_guide.map((line) => (
            <li key={line}>{line}</li>
          ))}
          <li>
            {data.meta.peptides_lt_10_aa.toLocaleString()} peptides are shorter than 10 amino acids and {data.meta.peptides_ge_10_aa.toLocaleString()} are 10 or longer; PC1 of the untrained embedding
            is correlated with length ({data.spaces[0].pc1_length_correlation.toFixed(2)}).
          </li>
        </ul>
      </Card>
    </div>
  );
}

export function EmbeddingPage() {
  const state = useApi(c1Api.embedding, []);
  return <DataState state={state} render={(data) => <EmbeddingBody data={data} />} />;
}
