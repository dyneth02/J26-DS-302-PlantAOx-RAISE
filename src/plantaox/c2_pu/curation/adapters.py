"""FR1 — source adapters for Multi-AOP and AnOxPePred (positive pool acquisition).

Each loader returns a standardized DataFrame keyed on a normalized ``sequence``
column (upper-cased, whitespace-stripped) with source-specific evidence columns
preserved. No filtering, deduplication, or tiering happens here — that is
``curation.standardize`` and ``curation.tiers``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from plantaox.c2_pu.common.sequence import normalize_sequence


def load_multiaop(path: str | Path) -> pd.DataFrame:
    """Load Multi-AOP's combined_data.csv.

    Returns columns: sequence, label. The ``name`` and ``SEQUENCE_space``
    columns are dropped — ``name`` is a leftover train/test split tag
    ("AntioxidantTrain" or a bare fold index), not a provenance identifier,
    and carries no assay-type information. Per AGENTS.md, only label == 1
    rows are ever treated as positive evidence; label == 0 rows are kept in
    the returned frame (for transparency/debugging) but must never be used
    as confirmed negatives downstream.
    """
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "sequence": df["SEQUENCE"].map(normalize_sequence),
            "label": df["label"].astype(int),
        }
    )
    return out


def load_anoxpepred(path: str | Path) -> pd.DataFrame:
    """Load AnOxPePred's Supplementary Data S1 (Marcatili).

    Returns columns: sequence, frs, chelator, source. FRS (free-radical
    scavenging) and Chelator (metal chelation) are independent per-sequence
    assay readouts — either one being 1 counts as confirmed antioxidant
    activity (see proposal p.12: AOP activity is attributed to these two
    mechanisms). A sequence is only a genuine external-control candidate
    when BOTH are 0.
    """
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "sequence": df["Sequence"].map(normalize_sequence),
            "frs": df["FRS"].astype(int),
            "chelator": df["Chelator"].astype(int),
            "source": df["Source"].astype(str),
        }
    )
    return out
