import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  DeltaDistributionBin,
  MetricChartPoint,
  PredictionFlipPoint,
  ScoreExamplePoint,
} from "@/features/c3-aop-bcs/types";

const TOOLTIP_STYLE = {
  background: "var(--color-surface)",
  borderColor: "var(--color-border)",
  color: "var(--color-text)",
};

const SERIES_COLORS = {
  P1: "#dc2626",
  P2: "var(--color-primary)",
  P3: "var(--color-accent)",
};

const GRID = "var(--color-border)";
const MUTED = "var(--color-text-muted)";

function percentage(value: number) {
  return Number((value * 100).toFixed(2));
}

export function DeltaDistributionChart({ data }: { data: DeltaDistributionBin[] }) {
  const chartData = data.map((row) => ({
    ...row,
    P1: percentage(row.P1),
    P2: percentage(row.P2),
    P3: percentage(row.P3),
  }));

  return (
    <div className="c3-chart" role="img" aria-label="Absolute DeltaScore percentage distributions for P1, P2, and P3">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 18, left: 4, bottom: 12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
          <XAxis
            dataKey="binMidpoint"
            type="number"
            domain={[0, 0.5]}
            ticks={[0, 0.1, 0.2, 0.3, 0.4, 0.5]}
            tickFormatter={(value) => Number(value).toFixed(1)}
            stroke={MUTED}
            fontSize={11}
            label={{ value: "Absolute DeltaScore", position: "insideBottom", offset: -8, fontSize: 11 }}
          />
          <YAxis
            domain={[0, "auto"]}
            stroke={MUTED}
            fontSize={11}
            tickFormatter={(value) => `${value}%`}
            label={{ value: "% of edits", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(value) => `Bin midpoint ${Number(value).toFixed(3)}`} />
          <Legend verticalAlign="top" height={32} />
          <ReferenceLine x={0.05} stroke="var(--color-warning-text)" strokeDasharray="5 4" label={{ value: "δ=.05", fill: "var(--color-warning-text)", fontSize: 10 }} />
          <Line type="monotone" dataKey="P1" stroke={SERIES_COLORS.P1} strokeWidth={2.5} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="P2" stroke={SERIES_COLORS.P2} strokeWidth={2.5} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="P3" stroke={SERIES_COLORS.P3} strokeWidth={2.5} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ScoreExamplesChart({ data }: { data: ScoreExamplePoint[] }) {
  return (
    <div className="c3-chart" role="img" aria-label="Original and perturbed scores for six inspected examples">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 18, left: 4, bottom: 54 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
          <XAxis dataKey="label" stroke={MUTED} fontSize={10} angle={-25} textAnchor="end" interval={0} height={68} />
          <YAxis domain={[0, 1]} stroke={MUTED} fontSize={11} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend verticalAlign="top" height={32} />
          <Bar dataKey="original" name="Original score" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="perturbed" name="Perturbed score" fill="var(--color-accent)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MetricSummaryChart({ data }: { data: MetricChartPoint[] }) {
  const chartData = data.map((row) => ({ ...row, value: percentage(row.value) }));
  const colors = ["var(--color-primary)", "#dc2626", "var(--color-accent)", "#2563eb"];
  return (
    <div className="c3-chart" role="img" aria-label="IR, FSR, BCS, and PFR percentage summary">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 18, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
          <XAxis dataKey="metric" stroke={MUTED} fontSize={12} />
          <YAxis domain={[0, 100]} stroke={MUTED} fontSize={11} tickFormatter={(value) => `${value}%`} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey="value" name="Pilot value (%)" radius={[5, 5, 0, 0]}>
            {chartData.map((row, index) => <Cell key={row.metric} fill={colors[index]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PredictionFlipChart({ data }: { data: PredictionFlipPoint[] }) {
  const chartData = data.map((row) => ({
    ...row,
    ratePercent: percentage(row.rate),
    detail: `${row.flips}/${row.total}`,
  }));
  return (
    <div className="c3-chart" role="img" aria-label="Prediction flip rates for P1, P2, and P3">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 18, left: 4, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
          <XAxis dataKey="type" stroke={MUTED} fontSize={12} />
          <YAxis domain={[0, 25]} stroke={MUTED} fontSize={11} tickFormatter={(value) => `${value}%`} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey="ratePercent" name="Prediction flip rate (%)" radius={[5, 5, 0, 0]}>
            {chartData.map((row) => <Cell key={row.type} fill={SERIES_COLORS[row.type]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
