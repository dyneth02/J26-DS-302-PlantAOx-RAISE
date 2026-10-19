"""Metal-chelation retrieval results (Steps 4-6), read from the accepted tables."""

from __future__ import annotations

from backend.app.schemas.c1_procon import (
    CollapseRow,
    PairedRow,
    RetrievalResponse,
    RetrievalRow,
    ScaleRow,
    SeedRow,
)
from backend.app.services.c1_procon.artifacts import num, read_csv, req

MODE = "strict"


def get_retrieval() -> RetrievalResponse:
    ret = read_csv("results/step5_mc_retrieval.csv")
    ret = ret[ret["mode"] == MODE]
    chance_row = ret[ret["kind"] == "chance"].iloc[0]

    representations = [
        RetrievalRow(
            representation=str(r["representation"]),
            kind=str(r["kind"]),
            ap=req(r["AP"]),
            ap_lo=num(r["AP_lo"]),
            ap_hi=num(r["AP_hi"]),
            lift=req(r["lift"]),
            recall_at_5=req(r["R@5"]),
            chance_recall_at_5=req(r["chance_R@5"]),
        )
        for _, r in ret.iterrows()
    ]

    paired_df = read_csv("results/step5_paired_comparisons.csv")
    paired_df = paired_df[paired_df["mode"] == MODE]
    paired = [
        PairedRow(
            comparison=str(r["comparison"]),
            ap_a=req(r["AP_A"]),
            ap_b=req(r["AP_B"]),
            delta_ap=req(r["delta_AP"]),
            ci_lo=req(r["ci_lo"]),
            ci_hi=req(r["ci_hi"]),
            p_holm=req(r["p_holm"]),
            verdict=str(r["verdict"]),
        )
        for _, r in paired_df.iterrows()
    ]

    seeds_df = read_csv("results/step6_seed_spread.csv")
    seeds = [
        SeedRow(
            model=str(r["model"]),
            ap_mean=req(r["AP_mean"]),
            ap_sd=req(r["AP_sd"]),
            delta_ap_mean=req(r["dAP_mean"]),
            seeds_below_untrained=int(r["seeds_below_raw"]),
            n_seeds=int(r["n"]),
        )
        for _, r in seeds_df.iterrows()
    ]

    scale_df = read_csv("results/step6_scale_sweep.csv")
    scale = [
        ScaleRow(
            scale=str(r["scale"]),
            model=str(r["model"]),
            ap_untrained=req(r["raw_AP"]),
            ap_trained_mean=req(r["AP_mean"]),
            delta_ap_mean=req(r["dAP_mean"]),
            seeds_below_untrained=int(r["seeds_below_raw"]),
            n_seeds=int(r["n"]),
        )
        for _, r in scale_df.iterrows()
    ]

    geo = read_csv("results/step5_geometry_heldout.csv")
    geo = geo[geo["mode"] == MODE]
    collapse = [
        CollapseRow(
            model=str(r["model"]),
            mean_cos_heldout=req(r["mean_cos_heldout"]),
            eff_rank_heldout=req(r["eff_rank_heldout"]),
        )
        for _, r in geo.iterrows()
    ]

    total_runs = int(seeds_df["n"].sum())
    above = int(total_runs - seeds_df["seeds_below_raw"].sum())

    return RetrievalResponse(
        mode=MODE,
        n_queries=int(ret["n_queries"].dropna().iloc[0]),
        chance_ap=req(chance_row["AP"]),
        chance_recall_at_5=req(chance_row["chance_R@5"]),
        representations=representations,
        paired=paired,
        seeds=seeds,
        scale=scale,
        collapse=collapse,
        trained_runs_total=total_runs,
        trained_runs_above_untrained=above,
        note=(
            "Average precision (AP) for retrieving metal-chelating (MC-active) peptides from the held-out fold; "
            "higher is better and a random ranking scores the chance AP. The untrained embeddings and the simple "
            "length / composition baselines are the fair reference for every trained head."
        ),
    )
