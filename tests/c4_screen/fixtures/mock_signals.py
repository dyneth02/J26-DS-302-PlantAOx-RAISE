#!/usr/bin/env python
"""
mock_signals.py - provisional MOCK C1/C2/C3 signals + contract validator for C4 (PlantAOP-Screen).

Nothing produced here is a research result. Every output carries source="mock".

Contract status (Interface Spec v0.1, owned by C4, PROVISIONAL):
  FROZEN in the proposals : BCS = IR * (1 - FSR); primary delta = 0.05; sequence range 3-50 AA.
  C4-PROPOSED (not frozen): c3_bcs.json schema, length-bin boundaries, reliability-flag cutoffs,
                            join key (sequence), c2_prob / c1_sim schemas.
  Length bins 3-10 / 11-20 / 21-50 come from the C3 analysis document (working assumption).

Usage:
  python mock_signals.py generate --candidates candidates.parquet --out data/mock --seed 42 --inject 10
  python mock_signals.py validate --candidates candidates.parquet --dir data/mock

Candidate table needs a `sequence` column. Optional: `d_norm` in [0,1] (AD distance, normalised),
`tier` (1/2/3). Without d_norm the AD-dependent noise term is switched off.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCHEMA_VERSION = "c4-interface-0.1-provisional"
GENERATOR_VERSION = "mock_signals/0.1"
STD_AA = set("ACDEFGHIKLMNPQRSTVWY")
REDOX = set("WYHMC")
HYDROPHOBIC = set("AVILMFW")
LENGTH_BINS = [("3-10", 3, 10), ("11-20", 11, 20), ("21-50", 21, 50)]
MECHANISMS = ["ALL", "FRS", "CHEL"]
DELTA = 0.05

# Mean IR / FSR per length bin (mock). BCS means are about 0.44 / 0.72 / 0.79,
# so short peptides trigger the LOW path and longer ones the HIGH path.
BCS_PARAMS = {
    "3-10": dict(ir=0.80, fsr=0.45),
    "11-20": dict(ir=0.88, fsr=0.18),
    "21-50": dict(ir=0.90, fsr=0.12),
}
MECH_OFFSET = {"ALL": (0.0, 0.0), "FRS": (0.02, -0.03), "CHEL": (-0.04, 0.06)}

# C4-PROVISIONAL flag cutoffs. They live in C4 config, never in C3's file, because C3 sets its
# own thresholds empirically in Phase 2.
BCS_LOW_BELOW = 0.5
BCS_HIGH_AT_OR_ABOVE = 0.7


# ----------------------------------------------------------------------------- helpers
def length_bin(length: int) -> str:
    for name, lo, hi in LENGTH_BINS:
        if lo <= length <= hi:
            return name
    raise ValueError(f"length {length} outside 3-50 AA")


def reliability_flag(bcs: float, low=BCS_LOW_BELOW, high=BCS_HIGH_AT_OR_ABOVE) -> str:
    """Provisional C4 flag; show the raw BCS next to it on every card."""
    if bcs < low:
        return "LOW"
    return "HIGH" if bcs >= high else "MEDIUM"


def _zscore(x: np.ndarray) -> np.ndarray:
    sd = x.std()
    return (x - x.mean()) / sd if sd > 0 else np.zeros_like(x, dtype=float)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _latent_aop_like(seqs: pd.Series) -> np.ndarray:
    """Rule-based AOP-likeness: redox residues, hydrophobic fraction, short-length bonus."""
    lens = seqs.str.len().to_numpy(dtype=float)
    f_redox = np.array([sum(c in REDOX for c in s) for s in seqs]) / lens
    f_hydro = np.array([sum(c in HYDROPHOBIC for c in s) for s in seqs]) / lens
    raw = 3.0 * f_redox + 2.0 * f_hydro + 1.0 * (lens <= 10)
    return _zscore(raw)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ----------------------------------------------------------------------------- generators
def make_c2(df, z, d_norm, rng, inject_n):
    """Mock PROB_C2: calibrated-looking probability, low base rate, noisier far from the AD."""
    noise_sd = 0.6 * (1.0 + 1.5 * d_norm)  # heteroscedastic: weaker model confidence out-of-domain
    logit = -3.0 + 1.2 * z + rng.normal(0.0, noise_sd)
    prob = np.clip(_sigmoid(logit), 0.005, 0.995)

    injected = []
    if inject_n > 0 and "tier" in df.columns:
        tier3 = np.flatnonzero(df["tier"].to_numpy() == 3)
        if len(tier3):
            pick = rng.choice(tier3, size=min(inject_n, len(tier3)), replace=False)
            prob[pick] = rng.uniform(0.90, 0.97, size=len(pick))
            injected = df["sequence"].iloc[pick].tolist()

    out = pd.DataFrame({
        "sequence": df["sequence"].to_numpy(),
        "PROB_C2": prob.astype("float32"),
        "evidence_tier": "U",
        "model_id": "MOCK_PU_v0.1",
        "source": "mock",
    })
    return out, injected


def make_c1(df, z, d_norm, rng):
    """Mock SIM_C1: partly driven by AOP-likeness, partly by AD proximity, plus noise."""
    logit = 0.8 * z - 0.8 * _zscore(d_norm) + rng.normal(0.0, 0.7, size=len(df))
    return pd.DataFrame({
        "sequence": df["sequence"].to_numpy(),
        "SIM_C1": _sigmoid(logit).astype("float32"),
        "model_id": "MOCK_PROCON_v0.1",
        "source": "mock",
    })


def _beta(rng, mean, conc=150.0):
    mean = float(np.clip(mean, 0.02, 0.98))
    return float(rng.beta(mean * conc, (1 - mean) * conc))


def make_c3(rng):
    """Mock BCS strata. IR and FSR are sampled; BCS is ALWAYS computed from the frozen formula."""
    strata = []
    for name, _, _ in LENGTH_BINS:
        for mech in MECHANISMS:
            d_ir, d_fsr = MECH_OFFSET[mech]
            ir = _beta(rng, BCS_PARAMS[name]["ir"] + d_ir)
            fsr = _beta(rng, BCS_PARAMS[name]["fsr"] + d_fsr)
            strata.append({
                "mechanism": mech, "length_bin": name,
                "n_sequences": int(rng.integers(120, 400)),
                "IR": round(ir, 4), "FSR": round(fsr, 4),
                "BCS": round(ir * (1 - fsr), 4),
            })
    all_rows = [s for s in strata if s["mechanism"] == "ALL"]
    ir_o = float(np.mean([s["IR"] for s in all_rows]))
    fsr_o = float(np.mean([s["FSR"] for s in all_rows]))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "mock",
        "predictor": "PU-AOP",
        "delta": DELTA,
        "formula": "BCS = IR * (1 - FSR)",
        "length_bins": [b[0] for b in LENGTH_BINS],
        "overall": {"IR": round(ir_o, 4), "FSR": round(fsr_o, 4), "BCS": round(ir_o * (1 - fsr_o), 4)},
        "strata": strata,
    }


# ----------------------------------------------------------------------------- generate
def generate(candidates_path, out_dir, seed=42, inject=10):
    df = _read_table(candidates_path)
    if "sequence" not in df.columns:
        sys.exit("candidates file needs a 'sequence' column")
    df = df.drop_duplicates("sequence").reset_index(drop=True)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    d_norm = df["d_norm"].clip(0, 1).to_numpy(dtype=float) if "d_norm" in df.columns else np.zeros(len(df))
    z = _latent_aop_like(df["sequence"])
    r1, r2, r3 = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3))

    c1 = make_c1(df, z, d_norm, r1)
    c2, injected = make_c2(df, z, d_norm, r2, inject)
    c3 = make_c3(r3)

    p1, p2, p3 = out / "c1_sim.parquet", out / "c2_prob.parquet", out / "c3_bcs.json"
    c1.to_parquet(p1, index=False)
    c2.to_parquet(p2, index=False)
    p3.write_text(json.dumps(c3, indent=2))

    rho = pd.Series(c1["SIM_C1"]).corr(pd.Series(c2["PROB_C2"]), method="spearman")
    manifest = {
        "generator": GENERATOR_VERSION, "schema_version": SCHEMA_VERSION, "seed": seed,
        "n_candidates": int(len(df)),
        "spearman_SIM_vs_PROB": round(float(rho), 3),
        "injected_demo_cases": injected,
        "note": "MOCK DATA. Injected cases illustrate a hypothesis, not a finding. "
                "Never compute PARRS/Recall@K/MRR/EF@1% on these signals as results.",
        "files": {p.name: _sha256(p) for p in (p1, p2, p3)},
    }
    (out / "MOCK_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote mock signals for {len(df)} candidates to {out}  (Spearman SIM vs PROB = {rho:.2f})")
    return manifest


# ----------------------------------------------------------------------------- validate
def validate(candidates_path, mock_dir):
    df = _read_table(candidates_path)
    d = Path(mock_dir)
    errors = []

    seqs = df["sequence"]
    bad = seqs[~seqs.map(lambda s: isinstance(s, str) and 3 <= len(s) <= 50 and set(s) <= STD_AA)]
    if len(bad):
        errors.append(f"{len(bad)} candidate sequences violate 3-50 AA / standard-alphabet rule")

    for fname, col in (("c1_sim.parquet", "SIM_C1"), ("c2_prob.parquet", "PROB_C2")):
        p = d / fname
        if not p.exists():
            errors.append(f"missing {fname}")
            continue
        t = pd.read_parquet(p)
        for need in ("sequence", col, "source"):
            if need not in t.columns:
                errors.append(f"{fname}: missing column '{need}'")
        if col in t.columns:
            if t[col].isna().any():
                errors.append(f"{fname}: NaN in {col}")
            if ((t[col] < 0) | (t[col] > 1)).any():
                errors.append(f"{fname}: {col} outside [0,1]")
        if "sequence" in t.columns:
            if t["sequence"].duplicated().any():
                errors.append(f"{fname}: duplicate sequence keys")
            missing = set(seqs) - set(t["sequence"])
            if missing:
                errors.append(f"{fname}: {len(missing)} candidates have no row (coverage must be 100%)")

    p3 = d / "c3_bcs.json"
    if not p3.exists():
        errors.append("missing c3_bcs.json")
    else:
        c3 = json.loads(p3.read_text())
        for key in ("schema_version", "source", "predictor", "delta", "formula", "strata"):
            if key not in c3:
                errors.append(f"c3_bcs.json: missing key '{key}'")
        if c3.get("delta") != DELTA:
            errors.append(f"c3_bcs.json: delta {c3.get('delta')} != primary delta {DELTA}")
        for s in c3.get("strata", []):
            if abs(s["BCS"] - s["IR"] * (1 - s["FSR"])) > 1e-3:
                errors.append(f"c3_bcs.json: BCS != IR*(1-FSR) in stratum {s['mechanism']}/{s['length_bin']}")
        have = {s["length_bin"] for s in c3.get("strata", []) if s["mechanism"] == "ALL"}
        needed = {length_bin(len(s)) for s in seqs if isinstance(s, str) and 3 <= len(s) <= 50}
        if needed - have:
            errors.append(f"c3_bcs.json: no ALL-mechanism stratum for length bins {sorted(needed - have)}")

    if errors:
        print("CONTRACT VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("contract validation passed")


def _read_table(path):
    path = Path(path)
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--candidates", required=True)
    g.add_argument("--out", default="data/mock")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--inject", type=int, default=10, help="Tier-3 demo cases given PROB_C2 >= 0.9")
    v = sub.add_parser("validate")
    v.add_argument("--candidates", required=True)
    v.add_argument("--dir", default="data/mock")
    a = ap.parse_args()
    if a.cmd == "generate":
        generate(a.candidates, a.out, a.seed, a.inject)
    else:
        validate(a.candidates, a.dir)


if __name__ == "__main__":
    main()
