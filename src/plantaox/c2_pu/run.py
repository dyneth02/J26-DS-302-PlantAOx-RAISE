"""CLI entrypoints orchestrating each FR stage for Component 02.

Usage:
    python -m plantaox.c2_pu.run fr1-positives
"""

from __future__ import annotations

import argparse
import json
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
    build_cluster_report,
    clusters_to_dataframe,
    parse_cdhit_clusters,
    run_cdhit,
)
from plantaox.c2_pu.curation.splits import (
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
    conflict_df.to_csv(CONFLICT_LOG_PATH, index=False)
    external_control_df.to_csv(EXTERNAL_CONTROL_PATH, index=False)

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
    clusters_df.to_csv(CDHIT_CLUSTERS_PATH, sep="\t", index=False)

    report = build_cluster_report(clusters_df, positive_df, n_input_sequences=len(positive_df))

    rep_ids = clusters_df.loc[clusters_df["is_representative"], "peptide_id"]
    reduced_df = (
        positive_df[positive_df["peptide_id"].isin(rep_ids)]
        .sort_values("peptide_id")
        .reset_index(drop=True)
    )
    reduced_df.to_parquet(POSITIVE_POOL_CDHIT_PATH, index=False)

    with open(CDHIT_REPORT_PATH, "w", encoding="utf-8") as handle:
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
    with open(GRAPHPART_SPLIT_SUMMARY_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    excluded_df.to_csv(GRAPHPART_EXCLUDED_PATH, index=False)

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PU-AOP (Component 02) CLI")
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("fr1-positives", help="Build the conflict-resolved FR1 positive pool")
    sub.add_parser("fr1-cluster", help="CD-HIT 90% identity clustering (Bucket 1.5)")
    sub.add_parser("fr1-split", help="GraphPart 40% identity 5-fold split (Bucket 1.6)")
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
    return 1


if __name__ == "__main__":
    sys.exit(main())
