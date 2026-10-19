"""Mock/real signal score and per-plant deterministic ranking."""

from __future__ import annotations

import pandas as pd


def score_candidates(joined: pd.DataFrame, memberships: pd.DataFrame, candidates: pd.DataFrame,
                     config: dict) -> pd.DataFrame:
    required = {"peptide_id", "sequence", "d_norm", "tier", "embedded", "SIM_C1", "PROB_C2",
                "SIM_C1_source", "PROB_C2_source", "cloud_source"}
    missing = required - set(joined.columns)
    if missing:
        raise ValueError(f"score input missing columns: {sorted(missing)}")
    eligible = joined.loc[joined.embedded.astype(bool)].copy()
    eligible = eligible.merge(memberships[["peptide_id", "plant"]], on="peptide_id", how="inner", validate="one_to_many")
    features = candidates.drop_duplicates("peptide_id").set_index("peptide_id")
    sequences = eligible.peptide_id.map(features.sequence)
    if not sequences.eq(eligible.sequence).all():
        raise ValueError("candidate/tier peptide_id and sequence mismatch")
    for col in ("molecular_weight", "isoelectric_point", "gravy", "net_charge_ph7", "length", "provenance"):
        if col in features.columns:
            eligible[col] = eligible.peptide_id.map(features[col])
    weights = config.get("weights", {})
    w1, w2 = float(weights.get("w1", .5)), float(weights.get("w2", .5))
    if w1 < 0 or w2 < 0 or abs(w1 + w2 - 1.0) > 1e-8:
        raise ValueError("scoring weights must be nonnegative and sum to 1")
    eligible["CS"] = w1 * eligible.SIM_C1 + w2 * eligible.PROB_C2 * (1.0 - eligible.d_norm)
    eligible.loc[eligible.tier.astype(int) == 3, "CS"] = 0.0
    if not eligible.CS.between(0, 1).all():
        raise ValueError("combined score outside [0,1]")
    eligible["rank"] = 0
    for plant, indices in eligible.groupby("plant", sort=True).groups.items():
        ordered = eligible.loc[indices].sort_values(["CS", "sequence"], ascending=[False, True], kind="stable")
        eligible.loc[ordered.index, "rank"] = range(1, len(ordered) + 1)
    return eligible.sort_values(["plant", "rank", "sequence"], kind="stable").reset_index(drop=True)
