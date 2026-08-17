"""Component 3 (AOP-BCS) prototype artifact generator.

Audits TWO real predictors with the same controlled perturbations of the same real
Component 1 AOP-BenchPos sequences, via a shared PredictorAdapter interface
(`.name`, `.score_batch(sequences) -> list[float]`) so the audit logic itself never
changes when the predictor under test changes -- this is the adapter pattern the
architecture doc calls for (C3 should audit *any* predictor without modification):

  - c2_logreg: this prototype's own Component 2 descriptor-only logistic regression.
  - multiaop_pretrained: a real, previously-trained external predictor (sequence xLSTM +
    molecular-graph MPNN hybrid, Research/my/data/raw/Multi-AOP, reported val accuracy
    0.906) -- auditing an actual published-style model, not just our own toy classifier.

Perturbations (shared across both predictors for a fair comparison):
  P1 - alanine scan of redox-active residues {W, Y, H, M, C}   (expected to matter)
  P2 - BLOSUM62-conservative substitution of a non-redox residue (expected NOT to matter)
  P3 - random substitution of a non-redox residue                (naive control)

Metric convention (the source doc leaves the exact IR/FSR formula loose, so it is fixed
and documented explicitly, same for both predictors):
  - Invariance Rate (IR): over P2, fraction of perturbed sequences whose predicted score
    moves by <= delta_threshold.
  - False Sensitivity Rate (FSR): over P2, fraction of perturbed sequences whose predicted
    *class label* flips across the 0.5 decision boundary despite the substitution being
    conservative and non-redox.
  - BCS = IR * (1 - FSR).
  - redox_sensitivity_rate (from P1, reported alongside BCS, not folded into it): fraction
    of alanine scans at redox residues that reduce the score by more than threshold.

Everything here (sequences, perturbations, both predictors, scores) is real.
"""
import json
import random
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from Bio.Align import substitution_matrices

from common_descriptors import compute_descriptors
from multiaop_model import MultiAOPPredictor

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "c3"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

REDOX_RESIDUES = set("WYHMC")
AA = list("ACDEFGHIKLMNPQRSTVWY")
DELTA_THRESHOLD = 0.05
N_AUDIT_SEQUENCES = 250

BLOSUM62 = substitution_matrices.load("BLOSUM62")


class LogRegPredictorAdapter:
    name = "c2_logreg"
    display_name = "C2 PU-AOP logistic regression (this prototype)"

    def __init__(self):
        bundle = joblib.load(ROOT / "artifacts" / "c2" / "pu_model.joblib")
        self.model, self.scaler, self.feature_cols = bundle["model"], bundle["scaler"], bundle["features"]

    def score_batch(self, sequences: list[str]) -> list[float]:
        rows = [compute_descriptors(s) for s in sequences]
        x = np.array([[r[c] for c in self.feature_cols] for r in rows])
        return self.model.predict_proba(self.scaler.transform(x))[:, 1].tolist()


class MultiAOPPredictorAdapter:
    name = "multiaop_pretrained"
    display_name = "Multi-AOP pretrained (xLSTM + graph MPNN, external, real checkpoint)"

    def __init__(self):
        self._predictor = MultiAOPPredictor()
        self.reported_val_metrics = self._predictor.reported_val_metrics
        self.reported_epoch = self._predictor.reported_epoch

    def score_batch(self, sequences: list[str]) -> list[float]:
        return self._predictor.score_batch(sequences)


def blosum_conservative_sub(residue: str) -> str:
    scores = {aa: BLOSUM62[residue, aa] for aa in AA if aa != residue}
    return max(scores, key=scores.get)


def random_sub(residue: str) -> str:
    return random.choice([aa for aa in AA if aa != residue])


def mutate_at(seq: str, pos: int, new_residue: str) -> str:
    return seq[:pos] + new_residue + seq[pos + 1:]


def build_perturbations(audit_set: pd.DataFrame) -> pd.DataFrame:
    """Generate P1/P2/P3 mutated sequences once, shared across every predictor audited."""
    rows = []
    for _, row in audit_set.iterrows():
        seq = row["sequence"]
        redox_positions = [i for i, c in enumerate(seq) if c in REDOX_RESIDUES]
        non_redox_positions = [i for i, c in enumerate(seq) if c not in REDOX_RESIDUES]

        p1_pos = random.choice(redox_positions)
        p1_seq = mutate_at(seq, p1_pos, "A")

        p2_pos = random.choice(non_redox_positions)
        p2_new = blosum_conservative_sub(seq[p2_pos])
        p2_seq = mutate_at(seq, p2_pos, p2_new)

        p3_pos = random.choice(non_redox_positions)
        p3_new = random_sub(seq[p3_pos])
        p3_seq = mutate_at(seq, p3_pos, p3_new)

        rows.append({
            "peptide_id": row["peptide_id"],
            "sequence": seq,
            "mechanism_tier": row["mechanism_tier"],
            "p1_alanine_position": p1_pos, "p1_alanine_residue": seq[p1_pos], "p1_sequence": p1_seq,
            "p2_conservative_position": p2_pos, "p2_original_residue": seq[p2_pos],
            "p2_new_residue": p2_new, "p2_sequence": p2_seq,
            "p3_random_position": p3_pos, "p3_original_residue": seq[p3_pos],
            "p3_new_residue": p3_new, "p3_sequence": p3_seq,
        })
    return pd.DataFrame(rows)


def audit_predictor(perturbations: pd.DataFrame, adapter) -> pd.DataFrame:
    results = perturbations.copy()
    t0 = time.time()
    results["original_score"] = np.round(adapter.score_batch(results["sequence"].tolist()), 4)
    results["p1_score"] = np.round(adapter.score_batch(results["p1_sequence"].tolist()), 4)
    results["p2_score"] = np.round(adapter.score_batch(results["p2_sequence"].tolist()), 4)
    results["p3_score"] = np.round(adapter.score_batch(results["p3_sequence"].tolist()), 4)
    print(f"  scored {len(results)}x4 sequences with {adapter.name} in {time.time() - t0:.1f}s")

    results["p1_delta"] = np.round(results["p1_score"] - results["original_score"], 4)
    results["p2_delta"] = np.round(results["p2_score"] - results["original_score"], 4)
    results["p3_delta"] = np.round(results["p3_score"] - results["original_score"], 4)
    return results


def compute_bcs_report(results: pd.DataFrame, adapter) -> dict:
    p2_delta = results["p2_delta"].values
    ir = float((np.abs(p2_delta) <= DELTA_THRESHOLD).mean())

    original_label = (results["original_score"].values >= 0.5).astype(int)
    p2_label = (results["p2_score"].values >= 0.5).astype(int)
    fsr = float((original_label != p2_label).mean())

    bcs = round(ir * (1 - fsr), 4)

    p1_delta = results["p1_delta"].values
    redox_sensitivity_rate = float((p1_delta <= -DELTA_THRESHOLD).mean())

    p3_delta = results["p3_delta"].values
    random_sensitivity_rate = float((np.abs(p3_delta) > DELTA_THRESHOLD).mean())

    if bcs >= 0.7:
        flag = "HIGH"
    elif bcs >= 0.4:
        flag = "MEDIUM"
    else:
        flag = "LOW"

    return {
        "predictor": adapter.name,
        "predictor_display_name": getattr(adapter, "display_name", adapter.name),
        "n_audited": int(len(results)),
        "delta_threshold": DELTA_THRESHOLD,
        "invariance_rate": round(ir, 4),
        "false_sensitivity_rate": round(fsr, 4),
        "bcs": bcs,
        "redox_sensitivity_rate": round(redox_sensitivity_rate, 4),
        "random_substitution_sensitivity_rate": round(random_sensitivity_rate, 4),
        "reliability_flag": flag,
        "metric_definitions": {
            "invariance_rate": "Fraction of BLOSUM62-conservative (P2) perturbations with |delta score| <= threshold.",
            "false_sensitivity_rate": "Fraction of P2 perturbations that flip the predicted class label despite being conservative.",
            "bcs": "IR * (1 - FSR)",
            "redox_sensitivity_rate": "Fraction of alanine scans (P1) at redox residues that reduce the score by more than threshold (higher is mechanistically better, not part of BCS).",
        },
    }


def main():
    positives = pd.read_parquet(ROOT / "data" / "processed" / "aop_sequences.parquet")
    has_redox = positives["sequence"].apply(lambda s: any(c in REDOX_RESIDUES for c in s))
    has_non_redox = positives["sequence"].apply(lambda s: any(c not in REDOX_RESIDUES for c in s))
    candidates = positives[has_redox & has_non_redox].copy()
    print(f"{len(candidates)} real AOP peptides contain a redox residue and a mutable non-redox residue")

    audit_set = candidates.sample(n=min(N_AUDIT_SEQUENCES, len(candidates)), random_state=RANDOM_SEED)
    perturbations = build_perturbations(audit_set)
    print(f"Auditing {len(audit_set)} real sequences, same perturbations shared across both predictors")

    adapters = [LogRegPredictorAdapter(), MultiAOPPredictorAdapter()]

    reliability_flags = {}
    bcs_reports = {}
    for adapter in adapters:
        print(f"Auditing predictor: {adapter.name}")
        results = audit_predictor(perturbations, adapter)

        results.to_parquet(ARTIFACT_DIR / f"perturbation_results__{adapter.name}.parquet", index=False)
        results.to_json(ARTIFACT_DIR / f"perturbation_results__{adapter.name}.json", orient="records", indent=2)

        bcs_report = compute_bcs_report(results, adapter)
        bcs_reports[adapter.name] = bcs_report
        (ARTIFACT_DIR / f"bcs_report__{adapter.name}.json").write_text(json.dumps(bcs_report, indent=2))
        print(f"  BCS = {bcs_report['bcs']} (IR={bcs_report['invariance_rate']}, "
              f"FSR={bcs_report['false_sensitivity_rate']}), flag={bcs_report['reliability_flag']}")

        reliability_flags[adapter.name] = {
            "display_name": bcs_report["predictor_display_name"],
            "bcs": bcs_report["bcs"],
            "flag": bcs_report["reliability_flag"],
        }

        example = results.iloc[0].to_dict()
        example_plot = {
            "predictor": adapter.name,
            "peptide_id": example["peptide_id"],
            "original_sequence": example["sequence"],
            "original_score": example["original_score"],
            "perturbations": [
                {"type": "P1_alanine_scan", "sequence": example["p1_sequence"], "score": example["p1_score"], "delta": example["p1_delta"]},
                {"type": "P2_blosum62_conservative", "sequence": example["p2_sequence"], "score": example["p2_score"], "delta": example["p2_delta"]},
                {"type": "P3_random_control", "sequence": example["p3_sequence"], "score": example["p3_score"], "delta": example["p3_delta"]},
            ],
        }
        (ARTIFACT_DIR / f"example_perturbation__{adapter.name}.json").write_text(json.dumps(example_plot, indent=2))

    (ARTIFACT_DIR / "predictor_reliability_flags.json").write_text(json.dumps(reliability_flags, indent=2))
    (ARTIFACT_DIR / "predictors.json").write_text(json.dumps(
        [{"key": a.name, "display_name": getattr(a, "display_name", a.name)} for a in adapters], indent=2
    ))

    multiaop_adapter = next(a for a in adapters if a.name == "multiaop_pretrained")
    summary = {
        "component": "C3_AOP_BCS",
        "prototype_mode": True,
        "data_mode": "real_sequences_real_predictors_real_perturbations",
        "n_audited": int(len(perturbations)),
        "predictors_audited": list(bcs_reports.keys()),
        "bcs_by_predictor": {k: v["bcs"] for k, v in bcs_reports.items()},
        "reliability_flag_by_predictor": {k: v["reliability_flag"] for k, v in bcs_reports.items()},
        "notes": [
            "Two real predictors are audited with the identical perturbation set, through a "
            "shared PredictorAdapter interface: this prototype's own Component 2 logistic "
            "regression, and a real previously-trained external model (Multi-AOP, sequence "
            "xLSTM + molecular-graph MPNN hybrid) loaded from its actual checkpoint.",
            f"The Multi-AOP checkpoint reports val accuracy {multiaop_adapter.reported_val_metrics.get('acc', 'n/a')} "
            f"at its own training epoch {multiaop_adapter.reported_epoch} -- that number is from the "
            "original authors' training run, not recomputed here.",
            "IR/FSR/BCS formulas are fixed conventions documented in each bcs_report__*.json's "
            "metric_definitions; the source architecture doc left the exact formula unspecified.",
        ],
    }
    (ARTIFACT_DIR / "c3_summary.json").write_text(json.dumps(summary, indent=2))
    print("Component 3 prototype artifacts generated successfully.")


if __name__ == "__main__":
    main()
