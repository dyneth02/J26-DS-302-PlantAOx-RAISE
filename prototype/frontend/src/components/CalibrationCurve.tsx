import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { CHART_GRID, CHART_TICK, CHART_LEGEND_STYLE, tooltipContentStyle, tooltipLabelStyle, tooltipItemStyle } from "./chartTheme";

export interface CalibrationBin {
  bin_center: number;
  confidence: number | null;
  accuracy: number | null;
  count: number;
  weight: number;
}

function toPoints(bins: CalibrationBin[]) {
  return bins
    .filter((b) => b.confidence !== null && b.accuracy !== null)
    .map((b) => ({ x: b.confidence, y: b.accuracy, z: b.count, weight: b.weight }));
}

// Reliability diagram: perfect calibration is the diagonal; points above it mean the
// model is under-confident there, points below mean over-confident.
export default function CalibrationCurve({
  selectedBins,
  hardBins,
  selectedLabel,
}: {
  selectedBins: CalibrationBin[];
  hardBins: CalibrationBin[];
  selectedLabel: string;
}) {
  const selectedPoints = toPoints(selectedBins);
  const hardPoints = toPoints(hardBins);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
        <CartesianGrid stroke={CHART_GRID} />
        <XAxis
          type="number"
          dataKey="x"
          name="confidence"
          domain={[0, 1]}
          tick={CHART_TICK}
          axisLine={{ stroke: CHART_GRID }}
          tickLine={false}
          label={{ value: "predicted confidence", position: "insideBottom", offset: -5, fill: "rgb(var(--c-ink-faint))", fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="accuracy"
          domain={[0, 1]}
          tick={CHART_TICK}
          axisLine={{ stroke: CHART_GRID }}
          tickLine={false}
          label={{ value: "observed accuracy", angle: -90, position: "insideLeft", fill: "rgb(var(--c-ink-faint))", fontSize: 11 }}
        />
        <ZAxis type="number" dataKey="z" range={[40, 240]} name="count" />
        <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="rgb(var(--c-ink-faint))" strokeDasharray="4 4" />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          contentStyle={tooltipContentStyle()}
          labelStyle={tooltipLabelStyle()}
          itemStyle={tooltipItemStyle()}
          formatter={(value: number, name: string) => [typeof value === "number" ? value.toFixed(3) : value, name]}
        />
        <Legend wrapperStyle={CHART_LEGEND_STYLE} />
        <Scatter name={selectedLabel} data={selectedPoints} fill="rgb(var(--c-teal))" fillOpacity={0.75} line shape="circle" />
        <Scatter name="hard pool" data={hardPoints} fill="rgb(var(--c-coral))" fillOpacity={0.75} line shape="circle" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
