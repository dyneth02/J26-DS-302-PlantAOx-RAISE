"""Confound controls (Step 8): source, length, split design and data size."""

from __future__ import annotations

import pandas as pd

from backend.app.schemas.c1_procon import (
    ConfoundRow,
    ConfoundsResponse,
    CvDesignRow,
    DeltaRow,
    LearningCurvePoint,
    LengthMatchedRow,
)
from backend.app.services.c1_procon.artifacts import num, read_csv, req

STEP8 = "results/step8/"


def _confound_rows(df: pd.DataFrame) -> list[ConfoundRow]:
    return [
        ConfoundRow(
            pool=str(r["pool"]),
            features=str(r["features"]),
            auroc=req(r["AUROC"]),
            lo=req(r["lo"]),
            hi=req(r["hi"]),
            above_null_97_5=bool(r["above_null_97_5"]),
        )
        for _, r in df.iterrows()
    ]


def get_confounds() -> ConfoundsResponse:
    strict = _confound_rows(read_csv(STEP8 + "step8_probe_strict.csv"))
    anox = _confound_rows(read_csv(STEP8 + "step8_probe_anoxpepred_only.csv"))

    delta_df = read_csv(STEP8 + "step8_delta_esm_over_confounds.csv")
    deltas = [
        DeltaRow(
            context=str(r["context"]),
            model=str(r["model"]),
            reference=str(r["reference"]),
            delta_auroc=req(r["delta_AUROC"]),
            lo=req(r["lo"]),
            hi=req(r["hi"]),
            repeats_delta_gt_0=int(r["repeats_delta_gt_0"]),
            verdict=str(r["verdict"]),
        )
        for _, r in delta_df.iterrows()
    ]

    lm_df = read_csv(STEP8 + "step8_length_matched.csv")
    length_matched = [
        LengthMatchedRow(
            features=str(r["features"]),
            pool=str(r["pool"]),
            auroc_mean=req(r["AUROC_mean"]),
            auroc_p2_5=req(r["AUROC_p2_5"]),
            auroc_p97_5=req(r["AUROC_p97_5"]),
            tripeptide_share_mc=num(r["tripeptide_share_MC"]),
            tripeptide_share_frs=num(r["tripeptide_share_FRS"]),
        )
        for _, r in lm_df.iterrows()
    ]

    lc_df = read_csv(STEP8 + "step8_learning_curve.csv")
    lc_df = lc_df[lc_df["pool"] == "strict"]
    learning_curve = [
        LearningCurvePoint(features=str(r["features"]), train_frac=req(r["train_frac"]), auroc=req(r["AUROC"]))
        for _, r in lc_df.iterrows()
    ]

    cv_df = read_csv(STEP8 + "step8_cv_design.csv")
    cv_design = [
        CvDesignRow(
            features=str(r["features"]),
            design=str(r["design"]),
            auroc_pooled=num(r["AUROC_pooled"]),
            auroc_foldmean=num(r["AUROC_foldmean"]),
        )
        for _, r in cv_df.iterrows()
    ]

    headline_df = read_csv(STEP8 + "step8_headline.csv")
    headline = {str(r["question"]): str(r["result"]) for _, r in headline_df.iterrows()}

    return ConfoundsResponse(
        verdict=(
            "After controlling for data source, length (tripeptide share) and homology, no ESM-2-specific "
            "mechanism signal remains; what is left is a weak composition-level difference (AUROC about 0.6)."
        ),
        strict=strict,
        anoxpepred_only=anox,
        esm_over_confounds=deltas,
        length_matched=length_matched,
        learning_curve=learning_curve,
        cv_design=cv_design,
        headline=headline,
    )
