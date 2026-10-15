import { FLAG_STYLES } from "./chartTheme";

// Extracts the `rounded-full ... label-tag ${FLAG_STYLES[flag]}` markup already
// duplicated across C1/C3/C4 into one place.
export default function Badge({
  flag,
  children,
}: {
  flag: keyof typeof FLAG_STYLES | string;
  children: React.ReactNode;
}) {
  const style = FLAG_STYLES[flag] ?? "bg-ink-faint/10 text-ink-faint ring-1 ring-line-strong";
  return (
    <span className={`label-tag inline-flex items-center rounded-full px-2.5 py-1 ${style}`}>
      {children}
    </span>
  );
}
