import { RefObject, useCallback, useState } from "react";
import html2canvas from "html2canvas";

// This is a self-hosted Vite app the user runs/builds/deploys themselves, not a
// sandboxed hosted-artifact iframe -- <a download> and canvas.toDataURL work unrestricted
// here. html2canvas has known limited fidelity with CSS masks / some pseudo-element
// gradients (the .panel::before hairline, the ambient body::before/after glow layers),
// so a full-page export may not capture those perfectly -- acceptable, since the
// content (charts/tables/panels) is what matters for the export use case.
export function useSnapshotExport(ref: RefObject<HTMLElement>) {
  const [exporting, setExporting] = useState(false);

  const exportPng = useCallback(
    async (filename: string) => {
      if (!ref.current) return;
      setExporting(true);
      try {
        const canvas = await html2canvas(ref.current, {
          backgroundColor: getComputedStyle(document.body).backgroundColor || "#000",
          useCORS: true,
          scale: Math.min(window.devicePixelRatio || 1, 2),
        });
        const link = document.createElement("a");
        link.download = `${filename}.png`;
        link.href = canvas.toDataURL("image/png");
        link.click();
      } finally {
        setExporting(false);
      }
    },
    [ref]
  );

  return { exportPng, exporting };
}
