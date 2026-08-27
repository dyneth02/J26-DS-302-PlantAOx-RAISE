export default function Slider({
  min,
  max,
  step = 0.01,
  value,
  onChange,
  formatValue = (v) => v.toFixed(2),
}: {
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  formatValue?: (value: number) => string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="flex items-center gap-3">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="slider-track h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-surface3 accent-lime"
        style={{
          background: `linear-gradient(to right, rgb(var(--c-lime)) ${pct}%, rgb(var(--c-surface3)) ${pct}%)`,
        }}
      />
      <span className="label-tag w-12 shrink-0 text-right text-lime">{formatValue(value)}</span>
    </div>
  );
}
