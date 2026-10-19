import type { Histogram, LengthDistribution, TierFraction, Plant } from "@/features/c4-screen/types";

const tierColors = ["#15803d", "#d97706", "#b91c1c"];

export function ADHistogram({ data }: { data: Histogram }) {
  const plot = { x: 42, y: 16, width: 540, height: 190 };
  const max = Math.max(1, ...data.cloud.counts, ...data.candidates.counts);
  const step = plot.width / data.bins;
  const xpos = (value: number) => plot.x + ((value - data.edges[0]) / (data.edges.at(-1)! - data.edges[0])) * plot.width;
  return (
    <div className="overflow-x-auto">
      <svg viewBox="0 0 610 250" role="img" aria-label={`Applicability-distance histogram for ${data.plant ?? "all plants"}; cloud versus candidates, with t1 and t2 thresholds`} className="min-w-[560px] w-full">
        <line x1={plot.x} y1={plot.y + plot.height} x2={plot.x + plot.width} y2={plot.y + plot.height} stroke="var(--color-border)" />
        {data.cloud.counts.map((value, index) => (
          <g key={`bin-${index}`}>
            <rect x={plot.x + index * step + step * .08} y={plot.y + plot.height - (value / max) * plot.height} width={step * .42} height={(value / max) * plot.height} fill="#7c3aed" opacity=".45">
              <title>Cloud bin {index + 1}: {value}</title>
            </rect>
            <rect x={plot.x + index * step + step * .52} y={plot.y + plot.height - (data.candidates.counts[index] / max) * plot.height} width={step * .42} height={(data.candidates.counts[index] / max) * plot.height} fill="#0f766e" opacity=".75">
              <title>Candidate bin {index + 1}: {data.candidates.counts[index]}</title>
            </rect>
          </g>
        ))}
        {[{ value: data.t1, label: "t1", color: "#d97706" }, { value: data.t2, label: "t2", color: "#b91c1c" }].map((threshold) => (
          <g key={threshold.label}>
            <line x1={xpos(threshold.value)} x2={xpos(threshold.value)} y1={plot.y} y2={plot.y + plot.height} stroke={threshold.color} strokeDasharray="5 4" strokeWidth="2" />
            <text x={xpos(threshold.value) + 3} y={plot.y + 12} fontSize="12" fill={threshold.color}>{threshold.label}</text>
          </g>
        ))}
        <text x={plot.x} y="232" fontSize="12" fill="var(--color-text-muted)">{data.edges[0].toFixed(3)} · cosine distance d_AD</text>
        <text x={plot.x + plot.width} y="232" textAnchor="end" fontSize="12" fill="var(--color-text-muted)">{data.edges.at(-1)?.toFixed(3)}</text>
      </svg>
      <div className="flex flex-wrap gap-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
        <span><i className="mr-1 inline-block h-2.5 w-2.5 bg-violet-700 opacity-60" />Reference cloud</span>
        <span><i className="mr-1 inline-block h-2.5 w-2.5 bg-teal-700" />Candidates</span>
        <span>Dashed lines: t1 and t2</span>
      </div>
    </div>
  );
}

export function TierStackedBars({ rows, plants }: { rows: TierFraction[]; plants?: Plant[] }) {
  const plantOrder = plants ?? [...new Set(rows.map((row) => row.plant).filter(Boolean) as Plant[])];
  const groups = plantOrder.flatMap((plant) => {
    const bins = [...new Set(rows.filter((row) => row.plant === plant).map((row) => row.length_bin).filter(Boolean))];
    return (bins.length ? bins : [undefined]).map((lengthBin) => ({
      plant,
      lengthBin,
      values: [1, 2, 3].map((tier) => rows.find((row) => row.plant === plant && row.length_bin === lengthBin && row.tier === tier)?.fraction ?? 0),
    }));
  });
  return (
    <div className="space-y-3" role="img" aria-label="Stacked tier fractions by plant and peptide length bin">
      {groups.map((group) => (
        <div key={`${group.plant}-${group.lengthBin ?? "overall"}`} className="grid grid-cols-[7rem_1fr_8rem] items-center gap-3 text-xs">
          <span>{group.plant}{group.lengthBin ? ` · ${group.lengthBin}` : ""}</span>
          <svg viewBox="0 0 500 22" role="img" aria-label={`${group.plant} ${group.lengthBin ?? "overall"}: Tier 1 ${(group.values[0] * 100).toFixed(1)} percent, Tier 2 ${(group.values[1] * 100).toFixed(1)} percent, Tier 3 ${(group.values[2] * 100).toFixed(1)} percent`} className="h-5 w-full overflow-hidden rounded">
            {group.values.map((value, index) => value > 0 ? <rect key={index} x={`${group.values.slice(0, index).reduce((sum, current) => sum + current, 0) * 500}`} y="0" width={`${value * 500}`} height="22" fill={tierColors[index]}><title>Tier {index + 1}: {(value * 100).toFixed(1)}%</title></rect> : null)}
          </svg>
          <span className="text-right" style={{ color: "var(--color-text-muted)" }}>T1 {(group.values[0] * 100).toFixed(0)}% · T2 {(group.values[1] * 100).toFixed(0)}% · T3 {(group.values[2] * 100).toFixed(0)}%</span>
        </div>
      ))}
      <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Tier 1 / Tier 2 / Tier 3, from left to right.</p>
    </div>
  );
}

export function LengthComparison({ rows }: { rows: LengthDistribution[] }) {
  const candidateTotal = rows.reduce((sum, row) => sum + row.candidate_count, 0) || 1;
  const cloudTotal = rows.reduce((sum, row) => sum + row.cloud_count, 0) || 1;
  const max = Math.max(0.001, ...rows.map((row) => Math.max(row.candidate_count / candidateTotal, row.cloud_count / cloudTotal)));
  return (
    <div className="space-y-2" role="img" aria-label="Candidate and reference-cloud sequence-length distributions">
      {rows.map((row) => {
        const cloudWidth = Math.min(100, row.cloud_count / cloudTotal / max * 100);
        const candidateWidth = Math.min(100, row.candidate_count / candidateTotal / max * 100);
        return <div key={row.length} className="grid grid-cols-[2rem_1fr] items-center gap-3 text-xs">
          <span>{row.length}</span>
          <svg viewBox="0 0 100 20" role="img" aria-label={`Length ${row.length}: cloud ${(row.cloud_count / cloudTotal * 100).toFixed(2)} percent, candidates ${(row.candidate_count / candidateTotal * 100).toFixed(2)} percent`} className="h-5 w-full">
            <rect x="0" y="1" width={cloudWidth} height="7" fill="#7c3aed"><title>Reference cloud: {row.cloud_count} peptides</title></rect>
            <rect x="0" y="11" width={candidateWidth} height="7" fill="#0f766e"><title>Candidates: {row.candidate_count} peptides</title></rect>
          </svg>
        </div>;
      })}
      <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Bars show within-source fractions (cloud first, candidates second).</p>
    </div>
  );
}
