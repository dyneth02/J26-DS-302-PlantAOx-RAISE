import { useState } from "react";
import { Outlet } from "react-router-dom";
import { C4Nav } from "@/features/c4-screen/components/C4Nav";

export function C4Shell() {
  const [presentationMode, setPresentationMode] = useState(false);

  return (
    <section className={`c4-screen space-y-5 ${presentationMode ? "c4-presentation" : ""}`}>
      <div
        role="status"
        className="rounded-lg border px-4 py-3 text-sm font-semibold"
        style={{ background: "var(--color-warning-bg)", borderColor: "var(--color-warning-border)", color: "var(--color-warning-text)" }}
      >
        MOCK REFERENCE CLOUD + MOCK SIGNALS — demonstration, not biological evidence
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>Component 04</p>
          <h2 className="text-xl font-bold">PlantAOP-Screen</h2>
        </div>
        <button
          type="button"
          aria-pressed={presentationMode}
          onClick={() => setPresentationMode((enabled) => !enabled)}
          className="rounded-lg border px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
          style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
        >
          {presentationMode ? "Exit presentation mode" : "Presentation mode"}
        </button>
      </div>
      <C4Nav />
      <Outlet />
    </section>
  );
}
