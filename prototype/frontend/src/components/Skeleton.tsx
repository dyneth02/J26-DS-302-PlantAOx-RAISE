export default function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg border border-line bg-surface2 ${className}`}
      aria-hidden="true"
    />
  );
}
