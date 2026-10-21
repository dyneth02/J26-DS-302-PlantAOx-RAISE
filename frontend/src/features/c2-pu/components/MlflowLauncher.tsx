import { useState } from "react";
import { Copy, ExternalLink, Check } from "lucide-react";

// A separate, locally-run MLflow UI (see mlflow_tracking/README.md) -- this
// component only ever opens it in a new tab or shows how to start it. It
// never embeds/iframes MLflow and never fetches its run data into this
// dashboard; that boundary is deliberate (see the plan this was built from).
const MLFLOW_URL = "http://127.0.0.1:5003";
const MLFLOW_COMMAND =
  "mlflow_tracking\\.venv\\Scripts\\mlflow.exe ui --backend-store-uri sqlite:///mlflow_tracking/mlflow.db --port 5003 --workers 1";

type LaunchState = "idle" | "checking" | "unreachable";

export function MlflowLauncher() {
  const [state, setState] = useState<LaunchState>("idle");
  const [copied, setCopied] = useState(false);

  const handleClick = async () => {
    setState("checking");
    try {
      // A `no-cors` request to a different local port resolves (opaque
      // response) if something is listening and answering, and throws if the
      // connection is refused. This is a reachability probe, not a real
      // request -- it needs no backend involvement and no CORS config on the
      // MLflow server.
      await fetch(MLFLOW_URL, { mode: "no-cors", signal: AbortSignal.timeout(1500) });
      window.open(MLFLOW_URL, "_blank", "noopener");
      setState("idle");
    } catch {
      setState("unreachable");
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(MLFLOW_COMMAND);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable (e.g. insecure context) -- the command is
      // still visible to select and copy manually.
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
        A separate, read-only MLflow view of C2 training runs (SO4 baselines, prior sensitivity, the
        curriculum, and the MCC reliability study). It is not part of this dashboard's API and does not
        affect the frozen PP1 release.
      </p>

      <button
        type="button"
        onClick={handleClick}
        disabled={state === "checking"}
        className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        style={{ background: "var(--color-primary)" }}
      >
        <ExternalLink size={16} />
        {state === "checking" ? "Checking..." : "Open MLflow UI"}
      </button>

      {state === "unreachable" && (
        <div
          className="rounded-lg border p-4 text-sm"
          style={{ borderColor: "var(--color-warning-border)", background: "var(--color-warning-bg)" }}
        >
          <p className="font-medium" style={{ color: "var(--color-warning-text)" }}>
            MLflow isn't running on {MLFLOW_URL}.
          </p>
          <p className="mt-1" style={{ color: "var(--color-warning-text)" }}>
            Start it in a terminal, then click "Open MLflow UI" again:
          </p>
          <div className="mt-2 flex items-start gap-2">
            <code
              className="flex-1 overflow-x-auto rounded px-2 py-1.5 font-mono text-xs"
              style={{ background: "var(--color-surface)", color: "var(--color-text)" }}
            >
              {MLFLOW_COMMAND}
            </code>
            <button
              type="button"
              onClick={handleCopy}
              aria-label="Copy command"
              className="flex shrink-0 items-center gap-1 rounded border px-2 py-1.5 text-xs font-medium"
              style={{ borderColor: "var(--color-warning-border)", color: "var(--color-warning-text)" }}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
