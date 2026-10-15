"""FR1 (Bucket 1.6) — GraphPart 40% identity homology-controlled split wrapper.

GraphPart's CLI/output schema was verified directly against the installed
package (`graphpart needle --help` and `graph_part.py`/`needle_utils.py`
source) rather than assumed from memory:

- ``-th``/``--threshold`` is specified in the SAME space as the raw metric
  (needle sequence identity, 1.0 = identical), and ``-tf one-minus`` (the
  CLI default) tells GraphPart to convert both the metric and the threshold
  to distance = 1 - identity internally. So "40% identity" is simply
  ``-th 0.4 -tf one-minus`` -- no manual 1-0.4 conversion needed, confirmed
  against graph_part.py's own docstring example.
- GraphPart's needle mode actually shells out to EMBOSS ``needleall``
  (batch all-vs-all alignment), not one ``needle`` call per pair, so runtime
  on ~1,000 short peptides is seconds-to-minutes, not hours.
- Output is a CSV indexed by the FASTA header (``AC``) with at minimum a
  ``cluster`` column (the partition/fold assignment, 0-indexed) -- renamed
  to ``fold`` here for clarity against this project's other fold-like
  concepts (CV folds vs CD-HIT clusters).
- GraphPart also writes `<out_file>_report.json` on its own, containing the
  "Min-threshold" achieved per removal round. That self-report is used
  directly for the cross-split homology validation (Bucket 2.4-style audit)
  instead of re-implementing pairwise alignment independently -- GraphPart's
  own job *is* computing exactly this distance, so re-deriving it would be
  redundant, not more rigorous.

Denominator choice (``-dn``), empirically re-derived, not assumed:
A first attempt used "shortest" (matching CD-HIT's own identity definition,
for cross-stage consistency) and this PARTITION COLLAPSED -- GraphPart
raised "Impossible to generate the desired 5 partitions... loss of 4
complete partitions." Root cause: 657 of 925 CD-HIT representatives (71%)
are under 10 AA, and "shortest"-denominator global-alignment identity for
very short peptides is dominated by chance matches (two 5-mers differing by
2 residues already clear 40% identity), so almost every pair of short
peptides looks "too similar," collapsing the partition graph into one giant
component. GraphPart's own default, "full" (alignment length including
gaps, which penalizes length-mismatched pairs), resolved this cleanly:
balanced folds, 841/925 retained (9% removed for genuine cross-fold
homology). CD-HIT (90% identity, near-duplicate *redundancy* removal) and
GraphPart (40% identity, cross-fold *leakage* prevention) are different
problems; forcing them to share an identity definition was the wrong
simplification, not a neutral consistency choice -- "full" is used here on
its own merits, confirmed empirically, not because it happened to work.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from plantaox.c2_pu.common.io import write_fasta
from plantaox.c2_pu.common.wsl import check_tool_available, run_in_conda_env, to_wsl_path

GRAPHPART_IDENTITY_THRESHOLD = 0.40  # matches the proposal's "GraphPart 40% identity" (SO1/SO2)
GRAPHPART_PARTITIONS = 5  # matches the proposal's "5-fold GraphPart homology-corrected CV" (abstract)
GRAPHPART_TRANSFORMATION = "one-minus"
# "full" (GraphPart's own default): alignment length including gaps, which
# penalizes identity for length-mismatched pairs. "shortest" (matching
# CD-HIT's definition) was tried first and caused the partition graph to
# collapse into one component -- see module docstring for the full story.
GRAPHPART_DENOMINATOR = "full"


class GraphPartNotAvailableError(RuntimeError):
    """Raised when graphpart/needleall cannot be invoked (WSL conda env not set up)."""


def check_graphpart_available(wsl_distro: str = "Ubuntu") -> bool:
    return check_tool_available("graphpart", wsl_distro=wsl_distro) and check_tool_available(
        "needleall", wsl_distro=wsl_distro
    )


def write_stratified_fasta(
    peptide_ids: list[str], sequences: list[str], evidence_tiers: list[str], out_path: Path
) -> None:
    """Write a FASTA with GraphPart's pipe-delimited metadata convention
    (``>id|tier=E1``) so ``-ln tier`` can balance E1/E2 representation across
    folds instead of leaving it to chance (see run_graphpart's ``labels_name``).
    """
    records = [
        (f"{pid}|tier={tier}", seq)
        for pid, seq, tier in zip(peptide_ids, sequences, evidence_tiers)
    ]
    write_fasta(out_path, records)


def run_graphpart(
    input_fasta: Path,
    output_csv: Path,
    threshold: float = GRAPHPART_IDENTITY_THRESHOLD,
    partitions: int = GRAPHPART_PARTITIONS,
    denominator: str = GRAPHPART_DENOMINATOR,
    labels_name: str | None = None,
    threads: int = 4,
    wsl_distro: str = "Ubuntu",
    timeout: float | None = 1800,
) -> tuple[Path, Path]:
    """Run GraphPart (needle mode) on ``input_fasta``.

    ``labels_name`` (e.g. "tier") enables GraphPart's own label-balancing: it
    tries to keep each label's count even across partitions subject to the
    homology constraint, which is what keeps E1/E2 proportions comparable
    across folds -- see write_stratified_fasta for the matching input format.

    Returns (output_csv, graphpart_report_json) -- the report path is
    GraphPart's own self-report, `<output_csv stem>_report.json`.
    """
    if not check_graphpart_available(wsl_distro):
        raise GraphPartNotAvailableError(
            f"graphpart/needleall not found in the WSL '{wsl_distro}' distro's pu_aop conda env. "
            "See IMPLEMENTATION_STATUS.md for setup "
            "(`pip install graph-part` + `micromamba install -c bioconda emboss`, inside the pu_aop env)."
        )

    wsl_in = to_wsl_path(input_fasta)
    wsl_out = to_wsl_path(output_csv)
    cmd = [
        "graphpart",
        "needle",
        "-ff",
        wsl_in,
        "-th",
        str(threshold),
        "-tf",
        GRAPHPART_TRANSFORMATION,
        "-pa",
        str(partitions),
    ]
    if labels_name:
        cmd += ["-ln", labels_name]
    cmd += [
        "-dn",
        denominator,
        "-of",
        wsl_out,
        "-nt",
        str(threads),
    ]
    result = run_in_conda_env(cmd, wsl_distro=wsl_distro, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"graphpart failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )

    report_path = output_csv.with_name(output_csv.stem + "_report.json")
    if not output_csv.exists() or not report_path.exists():
        raise RuntimeError(
            "graphpart reported success but expected output files are missing:\n"
            f"  splits: {output_csv} (exists={output_csv.exists()})\n"
            f"  report: {report_path} (exists={report_path.exists()})\n"
            f"stdout:\n{result.stdout}"
        )
    return output_csv, report_path


def load_graphpart_splits(output_csv: Path) -> pd.DataFrame:
    """Load GraphPart's split assignment CSV into a (peptide_id, fold) frame."""
    df = pd.read_csv(output_csv, index_col=0)
    df.index.name = "peptide_id"
    df = df.reset_index()
    if "cluster" not in df.columns:
        raise ValueError(
            f"Expected a 'cluster' column in GraphPart output, got columns: {df.columns.tolist()}"
        )
    return df.rename(columns={"cluster": "fold"})[["peptide_id", "fold"]]


def build_split_report(
    splits_df: pd.DataFrame,
    positive_df: pd.DataFrame,
    graphpart_report_path: Path,
    n_partitions_requested: int,
) -> tuple[dict, pd.DataFrame]:
    """Before/after summary: fold sizes, per-fold evidence-tier counts, and
    GraphPart's own homology-validation self-report (Min-threshold achieved,
    #problematic entities removed per round).

    Returns (summary_dict, excluded_df) -- excluded_df lists, by peptide_id,
    every sequence GraphPart removed to resolve a cross-fold homology
    violation. These have NO fold assignment and must not be silently
    back-filled into training/eval -- they are excluded from the CV
    framework entirely, which is why they are named explicitly here rather
    than just counted.
    """
    merged = splits_df.merge(
        positive_df[["peptide_id", "evidence_tier"]], on="peptide_id", how="left"
    )
    fold_sizes = merged.groupby("fold").size()
    tier_by_fold = (
        merged.groupby(["fold", "evidence_tier"]).size().unstack(fill_value=0)
    )

    with open(graphpart_report_path, encoding="utf-8") as handle:
        graphpart_self_report = json.load(handle)

    removal_rounds = {
        k: v
        for k, v in graphpart_self_report.items()
        if k.startswith("removal_step")
    }
    any_removal_needed = any(bool(v) for v in removal_rounds.values())

    excluded_ids = set(positive_df["peptide_id"]) - set(splits_df["peptide_id"])
    excluded_df = (
        positive_df[positive_df["peptide_id"].isin(excluded_ids)][
            ["peptide_id", "sequence", "length", "evidence_tier"]
        ]
        .assign(exclusion_reason="graphpart_cross_fold_homology_violation")
        .sort_values("peptide_id")
        .reset_index(drop=True)
    )

    summary = {
        "n_sequences": len(splits_df),
        "n_partitions_requested": n_partitions_requested,
        "n_partitions_produced": int(splits_df["fold"].nunique()),
        "fold_sizes": {str(k): int(v) for k, v in fold_sizes.items()},
        "fold_evidence_tier_counts": {
            str(k): {kk: int(vv) for kk, vv in row.items()}
            for k, row in tier_by_fold.to_dict(orient="index").items()
        },
        "any_homology_violation_removal_needed": any_removal_needed,
        "n_sequences_pre_removal": graphpart_self_report.get("samples_pre_removal"),
        "n_sequences_removed_for_homology": len(excluded_df),
    }
    return summary, excluded_df
