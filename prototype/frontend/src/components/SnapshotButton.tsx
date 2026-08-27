import { RefObject } from "react";
import { Camera, Loader2 } from "lucide-react";
import { useSnapshotExport } from "../hooks/useSnapshotExport";

export default function SnapshotButton({
  targetRef,
  filename,
}: {
  targetRef: RefObject<HTMLElement>;
  filename: string;
}) {
  const { exportPng, exporting } = useSnapshotExport(targetRef);
  return (
    <button
      onClick={() => exportPng(filename)}
      disabled={exporting}
      title="Download a PNG snapshot of this page"
      className="flex items-center gap-1.5 rounded-lg border border-line-strong bg-surface2 px-2.5 py-1.5 text-xs text-ink-dim transition-colors hover:border-lime/40 hover:text-ink disabled:opacity-50"
    >
      {exporting ? <Loader2 size={13} className="animate-spin" /> : <Camera size={13} />}
      <span className="label-tag">Snapshot</span>
    </button>
  );
}
