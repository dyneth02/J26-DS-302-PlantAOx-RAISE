"""Supervised probe (MC-active vs FRS-only) from the accepted Step 5 v4 tables."""

from __future__ import annotations

import pandas as pd

from backend.app.schemas.c1_procon import ProbePairedRow, ProbeResponse, ProbeRow
from backend.app.services.c1_procon.artifacts import num, read_csv, req

MODE = "strict"


def _row(r: pd.Series) -> ProbeRow:
    return ProbeRow(
        features=str(r["features"]),
        auroc=req(r["AUROC"]),
        lo=req(r["lo"]),
        hi=req(r["hi"]),
        rep_min=num(r.get("AUROC_rep_min")),
        rep_max=num(r.get("AUROC_rep_max")),
    )


def get_probe() -> ProbeResponse:
    df = read_csv("results/step5_probe.csv")
    df = df[df["mode"] == MODE]
    grouped_df = df[df["cv"].str.startswith("repeated grouped")]
    leaky_df = df[df["cv"].str.startswith("LEAKY")]

    null_band = _row(grouped_df[grouped_df["features"].str.startswith("NULL band")].iloc[0])
    # The one-draw noise row is not a chance reference (found_errors N-23); the 20-seed null band is.
    grouped = [
        _row(r)
        for _, r in grouped_df.iterrows()
        if not r["features"].startswith("NULL band") and not r["features"].startswith("RANDOM noise")
    ]
    leaky = [_row(r) for _, r in leaky_df.iterrows()]

    grouped_by_name = {p.features: p.auroc for p in grouped}
    inflation = {
        p.features: round(p.auroc - grouped_by_name[p.features], 3) for p in leaky if p.features in grouped_by_name
    }

    pdf = read_csv("results/step5_probe_paired.csv")
    pdf = pdf[pdf["mode"] == MODE]
    paired = [
        ProbePairedRow(
            model_a=str(r["A"]),
            model_b=str(r["B"]),
            delta_auroc=req(r["delta_AUROC"]),
            ci_lo=req(r["ci_lo"]),
            ci_hi=req(r["ci_hi"]),
            repeats_delta_gt_0=int(r["repeats_delta_gt_0"]),
            verdict=str(r["verdict"]),
        )
        for _, r in pdf.iterrows()
    ]

    return ProbeResponse(
        mode=MODE,
        evaluation_note=(
            "AUROC is the fold-mean over 50 test folds (5 folds x 10 repeats); whole homology groups stay in one fold. "
            "Confidence intervals are group bootstraps with the fitted models held fixed, so they are narrower than the "
            "true uncertainty. The probe separates MC-active from FRS-only labels, which are confounded with data source "
            "and tripeptide share, so a score here is not mechanism evidence."
        ),
        null_band=null_band,
        grouped=grouped,
        leaky=leaky,
        leakage_inflation=inflation,
        paired=paired,
    )
