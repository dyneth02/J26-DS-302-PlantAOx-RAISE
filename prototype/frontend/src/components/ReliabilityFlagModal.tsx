import { motion } from "framer-motion";
import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";
import Modal from "./Modal";
import { FLAG_STYLES } from "./chartTheme";

const FLAG_META: Record<string, { icon: typeof ShieldCheck; color: string; verdict: string }> = {
  HIGH: { icon: ShieldCheck, color: "rgb(var(--c-lime))", verdict: "Behaves consistently under conservative perturbation." },
  MEDIUM: { icon: ShieldAlert, color: "rgb(var(--c-amber))", verdict: "Partially consistent — some conservative edits flip the call." },
  LOW: { icon: ShieldX, color: "rgb(var(--c-coral))", verdict: "Inconsistent — conservative edits frequently flip the call." },
};

function FlowStep({ label, value, active }: { label: string; value: string; active?: boolean }) {
  return (
    <div
      className="rounded-lg border px-3 py-2 text-center"
      style={{
        borderColor: active ? "var(--c-lime)" : "var(--c-line-strong)",
        background: active ? "rgb(var(--c-lime) / 0.06)" : "transparent",
      }}
    >
      <p className="label-tag text-ink-faint">{label}</p>
      <p className="mt-0.5 font-data text-sm text-ink">{value}</p>
    </div>
  );
}

export default function ReliabilityFlagModal({
  open,
  onClose,
  predictorName,
  flag,
  bcs,
  invarianceRate,
  falseSensitivityRate,
}: {
  open: boolean;
  onClose: () => void;
  predictorName: string;
  flag: string;
  bcs: number;
  invarianceRate: number;
  falseSensitivityRate: number;
}) {
  const meta = FLAG_META[flag] ?? FLAG_META.MEDIUM;
  const Icon = meta.icon;

  return (
    <Modal open={open} onClose={onClose} title={`Reliability flag: ${flag}`}>
      <div className="flex items-start gap-4">
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 18 }}
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full"
          style={{ background: `${meta.color}1a` }}
        >
          <Icon size={26} color={meta.color} />
        </motion.div>
        <div>
          <span className={`inline-block rounded-full px-2.5 py-1 label-tag ${FLAG_STYLES[flag]}`}>{flag}</span>
          <p className="mt-1.5 text-sm text-ink-dim">{meta.verdict}</p>
          <p className="mt-0.5 text-xs text-ink-faint">{predictorName}</p>
        </div>
      </div>

      <p className="mt-5 label-tag text-ink-faint">How this flag was computed</p>
      <div className="mt-2 grid grid-cols-1 items-center gap-2 sm:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        <FlowStep label="IR" value={invarianceRate.toFixed(3)} />
        <span className="hidden text-center text-ink-faint sm:block">×</span>
        <FlowStep label="1 − FSR" value={(1 - falseSensitivityRate).toFixed(3)} />
        <span className="hidden text-center text-ink-faint sm:block">=</span>
        <FlowStep label="BCS" value={bcs.toFixed(4)} active />
        <span className="hidden text-center text-ink-faint sm:block">→</span>
        <FlowStep label="Flag" value={flag} active />
      </div>

      <ul className="mt-5 space-y-1.5 text-xs leading-relaxed text-ink-faint">
        <li>
          • BCS ≥ 0.70 → <strong className="text-lime">HIGH</strong>, 0.40 ≤ BCS &lt; 0.70 →{" "}
          <strong className="text-amber">MEDIUM</strong>, BCS &lt; 0.40 → <strong className="text-coral">LOW</strong> (real, fixed
          thresholds applied to this predictor's own BCS).
        </li>
        <li>
          • Invariance rate (IR) = fraction of BLOSUM62-conservative substitutions that left the score essentially unchanged (higher
          is better — the predictor should ignore a chemically-similar swap).
        </li>
        <li>
          • False sensitivity rate (FSR) = fraction of those same conservative substitutions that flipped the predicted class label
          despite being conservative (lower is better).
        </li>
      </ul>
    </Modal>
  );
}
