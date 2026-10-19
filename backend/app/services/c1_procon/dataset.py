"""Benchmark composition, computed on the fly from the accepted S2 table (read-only)."""

from __future__ import annotations

import pandas as pd

from backend.app.schemas.c1_procon import DatasetResponse, LabelCount, LengthBin, SourceByClass
from backend.app.services.c1_procon.artifacts import read_csv, read_json

LENGTH_BINS: list[tuple[str, int, int]] = [
    ("3", 3, 3),
    ("4", 4, 4),
    ("5", 5, 5),
    ("6", 6, 6),
    ("7", 7, 7),
    ("8", 8, 8),
    ("9-10", 9, 10),
    ("11-14", 11, 14),
    ("15+", 15, 10_000),
]
LABEL_ORDER = ["FRS", "FRS;MC", "MC", "GEN"]


def strict_pool(s2: pd.DataFrame) -> pd.DataFrame:
    """Mechanism-active peptides with per-peptide (strict) evidence.

    ``mc_active`` is True when the label contains MC (MC-only or FRS;MC) and False
    for FRS-only; GEN (mechanism not established) is never part of this pool.
    """
    mech = s2[s2["labels"].str.contains("FRS|MC")]
    pool = mech[mech["strict_evidence"].astype(str) == "True"].copy()
    pool["mc_active"] = pool["labels"].str.contains("MC")
    return pool


def load_s2() -> pd.DataFrame:
    return read_csv("AOP-BenchPos_S2.csv")


def get_dataset() -> DatasetResponse:
    s2 = load_s2()
    manifest = read_json("step1_manifest.json")
    pool = strict_pool(s2)
    mc, frs = pool[pool["mc_active"]], pool[~pool["mc_active"]]

    counts = s2["labels"].value_counts()
    label_counts = [LabelCount(label=lab, count=int(counts.get(lab, 0))) for lab in LABEL_ORDER]

    sources = sorted(pool["source_group"].dropna().unique())
    source_by_class = [
        SourceByClass(
            source_group=str(src),
            mc_active=int((mc["source_group"] == src).sum()),
            frs_only=int((frs["source_group"] == src).sum()),
        )
        for src in sources
    ]

    length_bins = [
        LengthBin(
            length_bin=name,
            mc_active=int(mc["length"].between(lo, hi).sum()),
            frs_only=int(frs["length"].between(lo, hi).sum()),
        )
        for name, lo, hi in LENGTH_BINS
    ]

    return DatasetResponse(
        fingerprint=manifest["s2_fingerprint"],
        split_type=str(manifest.get("split_type", "homology-grouped 2-fold split")),
        near_duplicate_rule=str(manifest.get("near_duplicate_rule", "")),
        label_counts=label_counts,
        strict_pool={"peptides": int(len(pool)), "mc_active": int(len(mc)), "frs_only": int(len(frs))},
        source_by_class=source_by_class,
        length_bins=length_bins,
        tripeptide_share={
            "mc_active": float((mc["length"] == 3).mean()),
            "frs_only": float((frs["length"] == 3).mean()),
        },
        mean_length={"mc_active": float(mc["length"].mean()), "frs_only": float(frs["length"].mean())},
        notes=[
            "GEN means the antioxidant mechanism is not established; it does not mean inactive.",
            "All FRS-only peptides come from AnOxPePred, so the data source alone separates the two classes (see Confounds).",
            "Mean lengths are almost equal; the real length confound is the tripeptide share.",
            "Tripeptides cannot be grouped by sequence similarity reliably, so some leakage risk remains for them.",
        ],
    )
