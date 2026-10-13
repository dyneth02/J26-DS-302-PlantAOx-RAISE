"""CLI entrypoints orchestrating each FR stage for Component 02.

Usage:
    python -m plantaox.c2_pu.run fr1-positives
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from plantaox.c2_pu.common.io import append_provenance_log, write_fasta
from plantaox.c2_pu.common.schemas import (
    CONFLICT_LOG_COLUMNS,
    EXTERNAL_CONTROL_COLUMNS,
    POSITIVE_POOL_COLUMNS,
)
from plantaox.c2_pu.curation.adapters import load_anoxpepred, load_multiaop
from plantaox.c2_pu.curation.dedup import (
    CDHIT_IDENTITY,
    CDHIT_THROWAWAY_LENGTH,
    CDHIT_WORD_LENGTH,
    build_cluster_report,
    clusters_to_dataframe,
    parse_cdhit_clusters,
    run_cdhit,
)
from plantaox.c2_pu.curation.freeze import freeze_baseline
from plantaox.c2_pu.curation.splits import (
    GRAPHPART_DENOMINATOR,
    GRAPHPART_IDENTITY_THRESHOLD,
    GRAPHPART_PARTITIONS,
    GRAPHPART_TRANSFORMATION,
    build_split_report,
    load_graphpart_splits,
    run_graphpart,
    write_stratified_fasta,
)
from plantaox.c2_pu.curation.tiers import build_positive_pool

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw" / "c2_pu"
INTERIM_DIR = REPO_ROOT / "data" / "interim" / "c2_pu"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

MULTIAOP_PATH = RAW_DIR / "Multi-AOP" / "combined_data.csv"
ANOXPEPRED_PATH = RAW_DIR / "AnOxPePred" / "Supplementary_Data_S1_Marcatili.csv"

POSITIVE_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CONFLICT_LOG_PATH = INTERIM_DIR / "label_conflicts_anox_vs_multiaop.csv"
EXTERNAL_CONTROL_PATH = PROCESSED_DIR / "anoxpepred_inactives_clean.csv"
PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr1_positive_pool_provenance.jsonl"

POSITIVE_POOL_FASTA_PATH = INTERIM_DIR / "aop_positives_provisional.fasta"
CDHIT_OUTPUT_PREFIX = INTERIM_DIR / "aop_positives_cdhit90"
CDHIT_CLUSTERS_PATH = PROCESSED_DIR / "cdhit_clusters.tsv"
CDHIT_REPORT_PATH = PROCESSED_DIR / "cdhit_before_after_report.json"
POSITIVE_POOL_CDHIT_PATH = PROCESSED_DIR / "aop_positives_cdhit90.parquet"

REP_FASTA_PATH = CDHIT_OUTPUT_PREFIX  # cd-hit writes representatives exactly to this path
GRAPHPART_INPUT_FASTA_PATH = INTERIM_DIR / "aop_positives_cdhit90_for_graphpart.fasta"
GRAPHPART_SPLITS_PATH = PROCESSED_DIR / "graphpart_splits.csv"  # canonical registry name
GRAPHPART_REPORT_PATH = PROCESSED_DIR / "graphpart_splits_report.json"
GRAPHPART_SPLIT_SUMMARY_PATH = PROCESSED_DIR / "graphpart_split_summary.json"
GRAPHPART_EXCLUDED_PATH = PROCESSED_DIR / "graphpart_excluded_for_homology.csv"

FR1_BASELINE_VERSION = "pp1_baseline_v1"
FROZEN_DIR = PROCESSED_DIR / "frozen" / FR1_BASELINE_VERSION

# Confirmed directly via `cd-hit -h`, `graphpart --help`, `needle -version`
# inside the pu_aop conda env (not assumed) -- see IMPLEMENTATION_STATUS.md.
TOOL_VERSIONS = {
    "cd-hit": "4.8.1",
    "graph-part": "1.0.2",
    "emboss_needleall": "6.6.0.0",
    "python_pipeline": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    "pandas": pd.__version__,
}


def run_fr1_positives(seed: int = 42) -> dict:
    """Bucket 1.3/1.4: build the conflict-resolved, evidence-tiered positive pool.

    NOT the FR1 freeze (Bucket 1.7) — CD-HIT 90% dedup (1.5) and GraphPart 40%
    splits (1.6) still need to run on this output before anything here can be
    called frozen.
    """
    mo_df = load_multiaop(MULTIAOP_PATH)
    an_df = load_anoxpepred(ANOXPEPRED_PATH)

    positive_df, conflict_df, external_control_df, summary = build_positive_pool(mo_df, an_df)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # peptide_id is a content-derived hash, so sorting by it is a fully
    # deterministic tie-break independent of Python's per-process hash-seed
    # randomization (set/dict iteration order is NOT guaranteed stable across
    # runs). This matters downstream: CD-HIT's representative selection for
    # exact-tie clusters depends on input FASTA order.
    positive_df = positive_df.reindex(columns=POSITIVE_POOL_COLUMNS).sort_values(
        "peptide_id"
    ).reset_index(drop=True)
    conflict_df = conflict_df.reindex(columns=CONFLICT_LOG_COLUMNS).sort_values(
        "peptide_id"
    ).reset_index(drop=True)
    external_control_df = external_control_df.reindex(columns=EXTERNAL_CONTROL_COLUMNS).sort_values(
        "peptide_id"
    ).reset_index(drop=True)

    positive_df.to_parquet(POSITIVE_POOL_PATH, index=False)
    conflict_df.to_csv(CONFLICT_LOG_PATH, index=False, lineterminator="\n")
    external_control_df.to_csv(EXTERNAL_CONTROL_PATH, index=False, lineterminator="\n")

    append_provenance_log(
        PROVENANCE_LOG_PATH,
        {
            "stage": "fr1_positive_pool_build",
            "multiaop_source": str(MULTIAOP_PATH),
            "anoxpepred_source": str(ANOXPEPRED_PATH),
            "seed": seed,
            "summary": summary,
            "outputs": {
                "positive_pool": str(POSITIVE_POOL_PATH),
                "conflict_log": str(CONFLICT_LOG_PATH),
                "external_control_clean": str(EXTERNAL_CONTROL_PATH),
            },
        },
    )
    return summary


def run_fr1_cluster() -> dict:
    """Bucket 1.5: CD-HIT 90% identity clustering of the provisional positive pool.

    Reads POSITIVE_POOL_PATH (written by run_fr1_positives) -- does not
    modify it. Writes a representatives-only FASTA, the cluster membership
    map (data_registry's canonical `cdhit_clusters.tsv`), a before/after
    report, and a reduced positive-pool parquet carrying forward each
    cluster's representative row (still not GraphPart-split -- see
    run_fr1_split, Bucket 1.6).
    """
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(
            f"{POSITIVE_POOL_PATH} not found -- run `fr1-positives` first."
        )
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    records = list(zip(positive_df["peptide_id"], positive_df["sequence"]))
    write_fasta(POSITIVE_POOL_FASTA_PATH, records)

    rep_fasta_path, clstr_path = run_cdhit(POSITIVE_POOL_FASTA_PATH, CDHIT_OUTPUT_PREFIX)

    members = parse_cdhit_clusters(clstr_path)
    clusters_df = clusters_to_dataframe(members)
    clusters_df.to_csv(CDHIT_CLUSTERS_PATH, sep="\t", index=False, lineterminator="\n")

    report = build_cluster_report(clusters_df, positive_df, n_input_sequences=len(positive_df))

    rep_ids = clusters_df.loc[clusters_df["is_representative"], "peptide_id"]
    reduced_df = (
        positive_df[positive_df["peptide_id"].isin(rep_ids)]
        .sort_values("peptide_id")
        .reset_index(drop=True)
    )
    reduced_df.to_parquet(POSITIVE_POOL_CDHIT_PATH, index=False)

    with open(CDHIT_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)

    append_provenance_log(
        PROVENANCE_LOG_PATH,
        {
            "stage": "fr1_cdhit90_clustering",
            "input": str(POSITIVE_POOL_PATH),
            "outputs": {
                "representative_fasta": str(rep_fasta_path),
                "clusters_tsv": str(CDHIT_CLUSTERS_PATH),
                "report": str(CDHIT_REPORT_PATH),
                "reduced_positive_pool": str(POSITIVE_POOL_CDHIT_PATH),
            },
            "report": report,
        },
    )
    return report


def run_fr1_split() -> dict:
    """Bucket 1.6: GraphPart 40% identity homology-controlled 5-fold split.

    Reads the CD-HIT representative FASTA (written by run_fr1_cluster) and
    the reduced positive pool -- does not modify either. Writes the frozen
    split assignment (`graphpart_splits.csv`, the canonical registry name)
    plus GraphPart's own homology-validation self-report.
    """
    if not REP_FASTA_PATH.exists() or not POSITIVE_POOL_CDHIT_PATH.exists():
        raise FileNotFoundError(
            f"{REP_FASTA_PATH} / {POSITIVE_POOL_CDHIT_PATH} not found -- run `fr1-cluster` first."
        )
    positive_df = pd.read_parquet(POSITIVE_POOL_CDHIT_PATH)

    write_stratified_fasta(
        positive_df["peptide_id"].tolist(),
        positive_df["sequence"].tolist(),
        positive_df["evidence_tier"].tolist(),
        GRAPHPART_INPUT_FASTA_PATH,
    )
    splits_csv_path, graphpart_report_path = run_graphpart(
        GRAPHPART_INPUT_FASTA_PATH, GRAPHPART_SPLITS_PATH, labels_name="tier"
    )
    splits_df = load_graphpart_splits(splits_csv_path)

    report, excluded_df = build_split_report(
        splits_df, positive_df, graphpart_report_path, n_partitions_requested=5
    )
    with open(GRAPHPART_SPLIT_SUMMARY_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
    excluded_df.to_csv(GRAPHPART_EXCLUDED_PATH, index=False, lineterminator="\n")

    append_provenance_log(
        PROVENANCE_LOG_PATH,
        {
            "stage": "fr1_graphpart_split",
            "input": str(GRAPHPART_INPUT_FASTA_PATH),
            "outputs": {
                "splits_csv": str(splits_csv_path),
                "graphpart_self_report": str(graphpart_report_path),
                "split_summary": str(GRAPHPART_SPLIT_SUMMARY_PATH),
                "excluded_for_homology": str(GRAPHPART_EXCLUDED_PATH),
            },
            "report": report,
        },
    )
    return report


def _git_commit_hash() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def run_fr1_freeze() -> Path:
    """Bucket 1.7: snapshot the validated FR1 artifacts under
    ``FR1_BASELINE_VERSION`` with a checksummed manifest.

    Does not re-validate anything -- run the acceptance test suite
    (tests/c2_pu/test_fr1_*.py) first. This only freezes what already passed.
    """
    required = {
        "aop_positives_provisional.parquet": POSITIVE_POOL_PATH,
        "aop_positives_cdhit90.parquet": POSITIVE_POOL_CDHIT_PATH,
        "cdhit_clusters.tsv": CDHIT_CLUSTERS_PATH,
        "cdhit_before_after_report.json": CDHIT_REPORT_PATH,
        "graphpart_splits.csv": GRAPHPART_SPLITS_PATH,
        "graphpart_excluded_for_homology.csv": GRAPHPART_EXCLUDED_PATH,
        "graphpart_splits_report.json": GRAPHPART_REPORT_PATH,
        "graphpart_split_summary.json": GRAPHPART_SPLIT_SUMMARY_PATH,
        "label_conflicts_anox_vs_multiaop.csv": CONFLICT_LOG_PATH,
        "anoxpepred_inactives_clean.csv": EXTERNAL_CONTROL_PATH,
    }

    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    cdhit_pool_df = pd.read_parquet(POSITIVE_POOL_CDHIT_PATH)
    splits_df = pd.read_csv(GRAPHPART_SPLITS_PATH)
    excluded_df = pd.read_csv(GRAPHPART_EXCLUDED_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)

    metadata = {
        "git_commit": _git_commit_hash(),
        "tool_versions": TOOL_VERSIONS,
        "config": {
            "cdhit": {
                "identity": CDHIT_IDENTITY,
                "word_length": CDHIT_WORD_LENGTH,
                "throwaway_length": CDHIT_THROWAWAY_LENGTH,
            },
            "graphpart": {
                "mode": "needle",
                "identity_threshold": GRAPHPART_IDENTITY_THRESHOLD,
                "transformation": GRAPHPART_TRANSFORMATION,
                "partitions": GRAPHPART_PARTITIONS,
                "denominator": GRAPHPART_DENOMINATOR,
                "labels_name": "tier",
            },
            "note": (
                "No stochastic steps exist in Buckets 1.1-1.6: positive-pool "
                "merge/conflict-resolution is deterministic threshold logic, "
                "CD-HIT's greedy clustering and GraphPart's slow-nn "
                "partitioning are both seed-free. Reproducibility here means "
                "'same inputs -> byte-identical outputs', verified directly, "
                "not 'same seed -> same sample'."
            ),
        },
        "counts": {
            "positive_pool_provisional": len(positive_df),
            "positive_pool_provisional_e1": int((positive_df["evidence_tier"] == "E1").sum()),
            "positive_pool_provisional_e2": int((positive_df["evidence_tier"] == "E2").sum()),
            "cdhit_clusters": len(cdhit_pool_df),
            "graphpart_retained": len(splits_df),
            "graphpart_excluded_for_homology": len(excluded_df),
            "label_conflicts_excluded": len(conflict_df),
            "external_control_clean": len(pd.read_csv(EXTERNAL_CONTROL_PATH)),
            "fold_sizes": {
                str(k): int(v) for k, v in splits_df["cluster"].value_counts().sort_index().items()
            },
        },
        "known_limitations": [
            "179 Multi-AOP positives contradicted by AnOxPePred's own assay call are excluded "
            "from both the positive pool and the external control, pending manual/supervisor "
            "review (label_conflicts_anox_vs_multiaop.csv).",
            "553 of the frozen positives (pre-CD-HIT) are E2 'provisional' -- Multi-AOP-only, "
            "no per-record assay metadata -- pending supervisor review.",
            "91 CD-HIT representatives (9.8%) were excluded by GraphPart to resolve cross-fold "
            "homology violations at the 40% identity threshold "
            "(graphpart_excluded_for_homology.csv).",
            "Fold 4 remains evidence-tier-skewed (64% E1) relative to the other folds (44-52%) "
            "even after label stratification -- a residual, not a defect, documented for "
            "awareness in per-fold metric comparisons.",
        ],
        "pending_supervisor_approvals": [
            "Conflict-resolution policy (assay evidence overrides Multi-AOP's label) -- "
            "2026-10-14 decision log.",
            "E2 provisional-tier default for Multi-AOP-only positives -- 2026-10-14 decision log.",
            "C1 source ambiguity (SwissProt vs UniRef50) -- unrelated to FR1 but still open, "
            "see PU_AOP_RESEARCH_CONTEXT.md section 4.",
        ],
    }

    manifest_path = freeze_baseline(FR1_BASELINE_VERSION, FROZEN_DIR, required, metadata)
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PU-AOP (Component 02) CLI")
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("fr1-positives", help="Build the conflict-resolved FR1 positive pool")
    sub.add_parser("fr1-cluster", help="CD-HIT 90% identity clustering (Bucket 1.5)")
    sub.add_parser("fr1-split", help="GraphPart 40% identity 5-fold split (Bucket 1.6)")
    sub.add_parser("fr1-freeze", help="Snapshot validated FR1 artifacts as a versioned baseline (Bucket 1.7)")
    args = parser.parse_args(argv)

    if args.stage == "fr1-positives":
        summary = run_fr1_positives()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr1-cluster":
        report = run_fr1_cluster()
        print(json.dumps(report, indent=2))
        return 0
    if args.stage == "fr1-split":
        report = run_fr1_split()
        print(json.dumps(report, indent=2))
        return 0
    if args.stage == "fr1-freeze":
        manifest_path = run_fr1_freeze()
        print(f"Frozen baseline written: {manifest_path}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
