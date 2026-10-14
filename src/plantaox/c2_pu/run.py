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

import numpy as np
import pandas as pd

from plantaox.c2_pu.common.io import append_provenance_log, read_fasta, write_fasta
from plantaox.c2_pu.common.wsl import run_in_conda_env, to_wsl_path
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
from plantaox.c2_pu.curation.peptipedia import build_c2_pool, extract_c2_candidates, load_activity_names
from plantaox.c2_pu.curation.c3 import (
    compute_fold_centroids,
    rank_candidates_for_fold,
    select_top_n_per_fold,
    validate_c3_fold_contract,
)
from plantaox.c2_pu.curation.audit import (
    cross_pool_homology_clusters,
    external_reference_screen,
    overlap_detail,
    pairwise_exact_overlap,
    sequence_integrity_report,
)
from plantaox.c2_pu.curation.biopep import BIOPEP_CITATION, BIOPEP_SEARCH_URL, fetch_biopep_by_activity
from plantaox.c2_pu.curation.uniref import fetch_uniref50_candidates, UNIREF50_QUERY, UNIREF50_SORT
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
from plantaox.c2_pu.common.sequence import is_valid_peptide, make_peptide_id
from plantaox.c2_pu.pools import (
    apply_secondary_blocklist,
    clean_c1_alphabet,
    clean_c1_cross_pool_overlap,
    clean_c1_pool,
    parse_uniprot_header,
)

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

# Bucket 2.1 — C1 random-decoy leakage cleanup. Raw inputs stay untouched
# (historical evidence, per the project owner's explicit instruction); the
# cleaned pool is a new PROCESSED artifact under the same canonical name.
C1_RAW_DECOYS_PATH = RAW_DIR / "UniProt_decoys" / "stage_c1_decoys.fasta"
C1_RAW_CANDIDATES_PATH = RAW_DIR / "UniProt_decoys" / "uniprotkb_candidates.fasta"
C1_CLEAN_FASTA_PATH = PROCESSED_DIR / "stage_c1_decoys.fasta"  # canonical name, processed tier
C1_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_leakage_exclusion_log.csv"
C1_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_leakage_replacement_log.csv"
C1_ACCESSION_MAP_PATH = PROCESSED_DIR / "c1_accession_map.csv"
C1_CLEAN_REPORT_PATH = PROCESSED_DIR / "c1_clean_report.json"
C1_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_c1_provenance.jsonl"

# Bucket 2.1 follow-up: standard-20-amino-acid alphabet policy (2026-10-14
# project-owner decision). The v1 artifacts above (post-leakage-fix,
# pre-alphabet-fix) are preserved untouched, per explicit instruction, rather
# than overwritten -- this is a separately versioned, superseding artifact.
C1_CLEAN_FASTA_V2_PATH = PROCESSED_DIR / "stage_c1_decoys_v2.fasta"
C1_ACCESSION_MAP_V2_PATH = PROCESSED_DIR / "c1_accession_map_v2.csv"
C1_ALPHABET_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_alphabet_exclusion_log.csv"
C1_ALPHABET_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_alphabet_replacement_log.csv"
C1_ALPHABET_FIX_REPORT_PATH = PROCESSED_DIR / "c1_alphabet_fix_report.json"

# Bucket 2.2 -- C2 bioactive unlabeled pool, built from the Peptipedia v2.0
# Zenodo dump (DOI 10.5281/zenodo.21488992), downloaded once and checksummed
# as a versioned raw source, per AGENTS.md rule 5.
C2_RAW_DUMP_PATH = RAW_DIR / "Peptipedia" / "peptipedia.20240323.sql.gz"
C2_FASTA_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled.fasta"  # canonical registry name
C2_ACTIVITY_MAP_PATH = PROCESSED_DIR / "c2_activity_map.csv"
C2_BUILD_REPORT_PATH = PROCESSED_DIR / "c2_build_report.json"
C2_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_c2_provenance.jsonl"


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


def run_fr2_c1_clean(seed: int = 42) -> dict:
    """Bucket 2.1 close-out: resolve C1/positive-pool leakage without a wholesale
    resample.

    Reads the RAW stage_c1_decoys.fasta and uniprotkb_candidates.fasta --
    does not modify either (historical evidence). Screens the existing 5,000
    C1 records against the full 1,205 FR1 positive pool AND the 179
    cross-source conflicts (conservative), removes any exact-sequence
    matches, and deterministically fills the gap from the untouched portion
    of the already-saved candidate pool (no live UniProt query needed).
    Writes the cleaned pool to the PROCESSED tier under the same canonical
    filename; the raw tier keeps the original, contaminated-but-historical
    file untouched.
    """
    if not (C1_RAW_DECOYS_PATH.exists() and C1_RAW_CANDIDATES_PATH.exists()):
        raise FileNotFoundError(f"{C1_RAW_DECOYS_PATH} / {C1_RAW_CANDIDATES_PATH} not found.")
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")

    c1_records = read_fasta(C1_RAW_DECOYS_PATH)
    candidate_pool_records = read_fasta(C1_RAW_CANDIDATES_PATH)
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"])

    clean_records, exclusion_log, replacement_log, summary = clean_c1_pool(
        c1_records, candidate_pool_records, screen_sequences, seed=seed
    )
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible replacement pool exhausted: needed {summary['n_replacements_needed']}, "
            f"only {summary['n_replacements_available']} available. Stopping rather than "
            "silently shipping a short pool -- see the project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C1_CLEAN_FASTA_PATH, clean_records)

    accession_map = pd.DataFrame(
        [
            {"peptide_header": h, "sequence": s, "length": len(s), **parse_uniprot_header(h)}
            for h, s in clean_records
        ]
    )
    accession_map.to_csv(C1_ACCESSION_MAP_PATH, index=False, lineterminator="\n")

    exclusion_df = pd.DataFrame(exclusion_log)
    exclusion_df.to_csv(C1_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")

    replacement_df = pd.DataFrame(replacement_log)
    replacement_df.to_csv(C1_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    unique_seqs = set(s for _, s in clean_records)
    lengths = [len(s) for s in unique_seqs]
    summary.update(
        {
            "seed": seed,
            "n_unique_sequences": len(unique_seqs),
            "min_length": min(lengths) if lengths else None,
            "max_length": max(lengths) if lengths else None,
            "screen_set_size": len(screen_sequences),
        }
    )
    with open(C1_CLEAN_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C1_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c1_leakage_cleanup",
            "raw_decoys": str(C1_RAW_DECOYS_PATH),
            "raw_candidates": str(C1_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta": str(C1_CLEAN_FASTA_PATH),
                "accession_map": str(C1_ACCESSION_MAP_PATH),
                "exclusion_log": str(C1_EXCLUSION_LOG_PATH),
                "replacement_log": str(C1_REPLACEMENT_LOG_PATH),
                "report": str(C1_CLEAN_REPORT_PATH),
            },
        },
    )
    return summary


def run_fr2_c1_alphabet_fix(seed: int = 42) -> dict:
    """Bucket 2.1 follow-up: enforce the standard-20-amino-acid-alphabet
    policy on C1 (2026-10-14 project-owner decision -- see Known Issues #9/#10
    in IMPLEMENTATION_STATUS.md).

    Starts from the v1 leakage-clean pool (``C1_CLEAN_FASTA_PATH``, the
    existing accepted Task 2.1 artifact) -- NOT the raw, still-leaky original
    -- and swaps every non-standard-alphabet record (X/B/Z/U) 1:1 for a
    standard-alphabet replacement drawn from the same candidate universe,
    re-screened against the secondary blocklist and all 1,205 FR1 positives
    + 179 conflicts. The v1 artifacts are left untouched; this writes a
    separately versioned v2 artifact set rather than overwriting them.
    """
    if not C1_CLEAN_FASTA_PATH.exists():
        raise FileNotFoundError(f"{C1_CLEAN_FASTA_PATH} not found -- run fr2-c1-clean first.")
    if not C1_RAW_CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"{C1_RAW_CANDIDATES_PATH} not found.")
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")

    c1_records = read_fasta(C1_CLEAN_FASTA_PATH)
    candidate_pool_records = read_fasta(C1_RAW_CANDIDATES_PATH)
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"])

    clean_records, exclusion_log, replacement_log, summary = clean_c1_alphabet(
        c1_records, candidate_pool_records, screen_sequences, seed=seed
    )
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible standard-alphabet replacement pool exhausted: needed "
            f"{summary['n_replacements_needed']}, only {summary['n_replacements_available']} "
            "available. Stopping rather than silently shipping a short pool -- see the "
            "project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C1_CLEAN_FASTA_V2_PATH, clean_records)

    accession_map = pd.DataFrame(
        [
            {"peptide_header": h, "sequence": s, "length": len(s), **parse_uniprot_header(h)}
            for h, s in clean_records
        ]
    )
    accession_map.to_csv(C1_ACCESSION_MAP_V2_PATH, index=False, lineterminator="\n")

    exclusion_df = pd.DataFrame(exclusion_log)
    exclusion_df.to_csv(C1_ALPHABET_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")

    replacement_df = pd.DataFrame(replacement_log)
    replacement_df.to_csv(C1_ALPHABET_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    unique_seqs = set(s for _, s in clean_records)
    lengths = [len(s) for s in unique_seqs]
    summary.update(
        {
            "seed": seed,
            "n_unique_sequences": len(unique_seqs),
            "min_length": min(lengths) if lengths else None,
            "max_length": max(lengths) if lengths else None,
            "screen_set_size": len(screen_sequences),
            "source_version": str(C1_CLEAN_FASTA_PATH),
            "output_version": str(C1_CLEAN_FASTA_V2_PATH),
        }
    )
    with open(C1_ALPHABET_FIX_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C1_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c1_alphabet_policy_fix",
            "source_version": str(C1_CLEAN_FASTA_PATH),
            "raw_candidates": str(C1_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta_v2": str(C1_CLEAN_FASTA_V2_PATH),
                "accession_map_v2": str(C1_ACCESSION_MAP_V2_PATH),
                "alphabet_exclusion_log": str(C1_ALPHABET_EXCLUSION_LOG_PATH),
                "alphabet_replacement_log": str(C1_ALPHABET_REPLACEMENT_LOG_PATH),
                "report": str(C1_ALPHABET_FIX_REPORT_PATH),
            },
        },
    )
    return summary


def run_fr2_c2_build(seed: int = 42) -> dict:
    """Bucket 2.2 -- build the C2 bioactive-unlabeled pool from the
    Peptipedia v2.0 Zenodo dump.

    The dump is parsed directly as a plain-text pg_dump stream (no database
    server needed, see curation/peptipedia.py). Inclusion policy, confirmed
    with the project owner: a peptide must have at least one *reported*
    (not merely absent) non-antioxidant bioactivity, must not itself be
    tagged Peptipedia's antioxidant activity (id 41, "Anti oxidative") even
    if it also carries other activity tags, must pass the shared 3-50 AA /
    standard-20-amino-acid-alphabet window, and must not exactly match any
    of the 1,205 FR1 positives or 179 cross-source conflicts (same
    conservative leakage screen used for C1). Experimentally-reported
    peptides are preferred over ML-predicted-only ones when sampling down
    to ~2,000 (mirrors the project's E1>E2 evidence precedence) -- in this
    run the experimental tier alone comfortably supplies the full 2,000.

    Known, explicitly-flagged gap (not done in this pass): the Planner's
    "cross-reference AODB and DFBP" item. Peptipedia's own 76 integrated
    source databases were checked directly (`source` table) and neither
    AODB nor DFBP is among them, so this pool is not yet cross-checked
    against those two specific resources -- flagged in
    IMPLEMENTATION_STATUS.md rather than silently treated as covered.
    """
    if not C2_RAW_DUMP_PATH.exists():
        raise FileNotFoundError(
            f"{C2_RAW_DUMP_PATH} not found -- download the Peptipedia v2.0 Zenodo dump "
            "(DOI 10.5281/zenodo.21488992, peptipedia.20240323.sql.gz) first."
        )
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")

    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"])

    activity_names = load_activity_names(C2_RAW_DUMP_PATH)
    sequences, activities = extract_c2_candidates(C2_RAW_DUMP_PATH)
    records, summary = build_c2_pool(sequences, activities, screen_sequences, seed=seed)
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible C2 candidate pool exhausted: needed {summary['n_requested']}, only "
            f"{summary['n_output_records']} assembled. Stopping rather than silently shipping "
            "a short pool -- see the project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fasta_records = [(make_peptide_id(r["sequence"], prefix="C2"), r["sequence"]) for r in records]
    write_fasta(C2_FASTA_PATH, fasta_records)

    activity_map = pd.DataFrame(
        [
            {
                "peptide_id": peptide_id,
                "id_peptide_peptipedia": r["id_peptide"],
                "sequence": r["sequence"],
                "length": r["length"],
                "activity_ids": ";".join(str(a) for a in r["activity_ids"]),
                "activity_names": ";".join(
                    activity_names.get(a, f"unknown_activity_{a}") for a in r["activity_ids"]
                ),
                "has_experimental_evidence": r["has_experimental_evidence"],
            }
            for (peptide_id, _), r in zip(fasta_records, records)
        ]
    )
    activity_map.to_csv(C2_ACTIVITY_MAP_PATH, index=False, lineterminator="\n")

    import hashlib

    dump_sha256 = hashlib.sha256(C2_RAW_DUMP_PATH.read_bytes()).hexdigest()
    summary.update(
        {
            "source_dump": str(C2_RAW_DUMP_PATH),
            "source_dump_sha256": dump_sha256,
            "source_dump_doi": "10.5281/zenodo.21488992",
            "screen_set_size": len(screen_sequences),
            "antioxidant_activity_id": 41,
            "antioxidant_activity_name": activity_names.get(41),
            "cross_reference_aodb_dfbp": "NOT DONE -- neither AODB nor DFBP is among Peptipedia's "
            "76 integrated source databases; see IMPLEMENTATION_STATUS.md Known Issues.",
        }
    )
    with open(C2_BUILD_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C2_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c2_bioactive_pool_build",
            "source_dump": str(C2_RAW_DUMP_PATH),
            "source_dump_sha256": dump_sha256,
            "source_dump_doi": "10.5281/zenodo.21488992",
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta": str(C2_FASTA_PATH),
                "activity_map": str(C2_ACTIVITY_MAP_PATH),
                "report": str(C2_BUILD_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 3.2 — ESM-2 embedding interface smoke test. torch/fair-esm live
# only in the WSL pu_aop conda env (installed there per the project owner's
# explicit decision, 2026-10-14: CPU-only, since the 35M-param model's
# workload doesn't benefit from this machine's ~1hr-download GPU stack) --
# this stage shells out via common/wsl.py, exactly like CD-HIT/GraphPart,
# rather than importing common.embeddings (which imports torch) directly
# into this Windows-side process.
ESM2_CLI_SCRIPT_PATH = Path(__file__).resolve().parent / "esm2_cli.py"
ESM2_SMOKETEST_INPUT_PATH = INTERIM_DIR / "esm2_smoketest_input.json"
ESM2_SMOKETEST_REPORT_PATH = PROCESSED_DIR / "esm2_smoketest_report.json"
ESM2_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr3_esm2_provenance.jsonl"

# Small, fixed set -- NOT full feature generation (that's a later, separate
# Bucket 3.2 task). Mix of length/composition classes mirroring Bucket 3.1's
# own "short/long/charged/hydrophobic" testing convention, so the smoke test
# exercises genuinely different embedding regions, not five near-identical
# inputs.
ESM2_SMOKETEST_PEPTIDES = {
    "SMOKE-SHORT": "KPEEDWGR",
    "SMOKE-MED": "MIRIISRANSVTSSNEVNRLVTGQIPHD",
    "SMOKE-CHARGED": "KKKKKEEEEE",
    "SMOKE-HYDROPHOBIC": "LLLVVVIIIAAA",
    "SMOKE-LONG": "MTPSLSSFLNSLILGAVIVVVPITLALLFVSQKDRTIR",
}


def run_esm2_smoke_test(force_cpu: bool = False) -> dict:
    """Bucket 3.2: configure PyTorch/fair-esm, freeze the ESM-2 spec, and
    smoke-test embedding extraction on a small fixed peptide set.

    Explicitly NOT full feature generation -- extracting embeddings for the
    full positive pool and C1/C2/C3 is a separate, later task. Writes only a
    summary report (shape/dtype/finiteness/norm per peptide); raw embedding
    vectors are never written to a committed path.
    """
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "peptide_ids": list(ESM2_SMOKETEST_PEPTIDES.keys()),
        "sequences": list(ESM2_SMOKETEST_PEPTIDES.values()),
        "force_cpu": force_cpu,
        "validate_alphabet": True,
    }
    with open(ESM2_SMOKETEST_INPUT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)

    result = run_in_conda_env(
        [
            "python",
            to_wsl_path(ESM2_CLI_SCRIPT_PATH),
            to_wsl_path(ESM2_SMOKETEST_INPUT_PATH),
            to_wsl_path(ESM2_SMOKETEST_REPORT_PATH),
        ],
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ESM-2 smoke test failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    if not ESM2_SMOKETEST_REPORT_PATH.exists():
        raise RuntimeError(
            "esm2_cli.py reported success but no report was written:\n" + result.stdout
        )

    with open(ESM2_SMOKETEST_REPORT_PATH, encoding="utf-8") as handle:
        report = json.load(handle)

    append_provenance_log(
        ESM2_PROVENANCE_LOG_PATH,
        {
            "stage": "bucket3_esm2_smoke_test",
            "input": str(ESM2_SMOKETEST_INPUT_PATH),
            "output": str(ESM2_SMOKETEST_REPORT_PATH),
            "summary": {k: v for k, v in report.items() if k != "per_peptide"},
        },
    )
    return report


# Bucket 2.3 — C3 ESM-2 hard-challenge pool, fold-safe by construction (see
# curation/c3.py's module docstring for the full leakage rationale).
C3_RAW_CANDIDATES_PATH = RAW_DIR / "UniRef50" / "uniref50_candidates.fasta"
C3_RAW_PROVENANCE_PATH = RAW_DIR / "UniRef50" / "uniref50_provenance.txt"
C3_TARGET_CANDIDATE_SIZE = 25_000
C3_TOP_N_PER_FOLD = 2_000

C3_POSITIVE_EMBEDDINGS_CACHE = INTERIM_DIR / "c3_positive_embeddings.npz"  # gitignored, regeneratable
C3_CANDIDATE_EMBEDDINGS_CACHE = INTERIM_DIR / "c3_candidate_embeddings.npz"  # gitignored, regeneratable
C3_EMBED_INPUT_PATH = INTERIM_DIR / "c3_embed_input.json"

C3_FASTA_PATH = PROCESSED_DIR / "stage_c3_esm2_hard_challenges.fasta"  # canonical registry name
C3_RANKING_PATH = PROCESSED_DIR / "c3_similarity_ranking.csv"
C3_BUILD_REPORT_PATH = PROCESSED_DIR / "c3_build_report.json"
C3_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_c3_provenance.jsonl"


def run_fr2_c3_fetch_candidates(target_size: int = C3_TARGET_CANDIDATE_SIZE) -> dict:
    """Bucket 2.3 step 1: acquire the UniRef50 candidate-fragment universe
    via a filtered REST query (not the ~13GB bulk FASTA, same reasoning
    already applied to C1 -- see curation/uniref.py). Writes a versioned raw
    snapshot; this is the frozen historical-evidence file all downstream C3
    code reads from -- it is not re-queried live on every pipeline run.
    """
    import datetime

    (RAW_DIR / "UniRef50").mkdir(parents=True, exist_ok=True)
    import time as _time

    start = _time.time()
    records = fetch_uniref50_candidates(target_size=target_size)
    elapsed = _time.time() - start

    write_fasta(C3_RAW_CANDIDATES_PATH, records)
    with open(C3_RAW_PROVENANCE_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("Stage C3 UniRef50 Candidate Universe - Provenance Log\n")
        handle.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
        handle.write("Source: UniProt REST API /uniref/search\n")
        handle.write(f"Query: {UNIREF50_QUERY}\n")
        handle.write(f"Sort: {UNIREF50_SORT}\n")
        handle.write(f"Target size: {target_size}\n")
        handle.write(f"Actual fetched: {len(records)}\n")
        handle.write(f"Fetch elapsed seconds: {elapsed:.1f}\n")

    return {"n_fetched": len(records), "target_size": target_size, "elapsed_seconds": elapsed}


def _embed_via_wsl(
    peptide_ids: list[str], sequences: list[str], cache_path: Path, label: str, force_cpu: bool = False
) -> dict[str, np.ndarray]:
    """Shell out to esm2_cli.py (inside the WSL pu_aop env) to embed a batch
    of sequences, caching the raw vectors at ``cache_path`` (gitignored --
    never committed, same "don't commit large embedding arrays" rule as
    model weights). Returns peptide_id -> float32 480-dim vector.
    """
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "peptide_ids": peptide_ids,
        "sequences": sequences,
        "force_cpu": force_cpu,
        "validate_alphabet": True,
        "batch_size": 64,
        "save_embeddings_path": to_wsl_path(cache_path),
    }
    with open(C3_EMBED_INPUT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)

    summary_report_path = INTERIM_DIR / f"c3_embed_{label}_report.json"
    result = run_in_conda_env(
        [
            "python",
            to_wsl_path(ESM2_CLI_SCRIPT_PATH),
            to_wsl_path(C3_EMBED_INPUT_PATH),
            to_wsl_path(summary_report_path),
        ],
        timeout=1800,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ESM-2 embedding of {label} failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}")
    if not cache_path.exists():
        raise RuntimeError(f"esm2_cli.py reported success but no embedding cache was written for {label}:\n{result.stdout}")

    with np.load(cache_path, allow_pickle=False) as npz:
        ids = npz["peptide_ids"]
        matrix = npz["embeddings"]
    return {pid: matrix[i] for i, pid in enumerate(ids)}


def run_fr2_c3_build(force_cpu: bool = False) -> dict:
    """Bucket 2.3 step 2: fold-safe ESM-2 hard-challenge selection.

    For each of GraphPart's 5 training folds, fits a positive-pool centroid
    using ONLY that fold's training partition (the other 4 folds' 834
    frozen positives -- see curation/c3.py's docstring for why this must
    never include the held-out fold's own positives), ranks the shared
    UniRef50 candidate universe by cosine similarity to that fold-specific
    centroid, and selects each fold's own top-2,000 hardest candidates.
    The exported FASTA is the union of all 5 folds' selections (deduplicated
    by sequence); ``c3_similarity_ranking.csv`` records per-fold membership
    and rank/similarity explicitly, so a downstream consumer training on
    fold k can (and must) filter to that fold's own rows only -- using a
    different fold's selection would silently reintroduce the exact
    selection-leakage this construction exists to prevent.

    Known, explicitly-flagged gap (not done in this pass): the Planner's
    "screen known-AOP matches against AODB, DFBP, BIOPEP-UWM" item. Only
    Multi-AOP/AnOxPePred-derived FR1 positives + 179 conflicts are screened
    (same exact-sequence leakage check used for C1/C2); AODB/DFBP/BIOPEP-UWM
    remain unintegrated project-wide (see IMPLEMENTATION_STATUS.md).
    """
    if not C3_RAW_CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"{C3_RAW_CANDIDATES_PATH} not found -- run fr2-c3-fetch-candidates first.")
    if not GRAPHPART_SPLITS_PATH.exists():
        raise FileNotFoundError(f"{GRAPHPART_SPLITS_PATH} not found -- run fr1-split first.")
    if not POSITIVE_POOL_CDHIT_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_CDHIT_PATH} not found -- run fr1-cluster first.")

    splits_df = pd.read_csv(GRAPHPART_SPLITS_PATH)
    positives_df = pd.read_parquet(POSITIVE_POOL_CDHIT_PATH)
    training_df = splits_df.merge(positives_df, left_on="AC", right_on="peptide_id", how="inner")
    if len(training_df) != len(splits_df):
        raise RuntimeError("Some GraphPart-split peptide IDs are missing a sequence in the CD-HIT pool.")
    fold_of = dict(zip(training_df["peptide_id"], training_df["cluster"].astype(int)))
    n_folds = int(training_df["cluster"].max()) + 1

    raw_candidates = read_fasta(C3_RAW_CANDIDATES_PATH)
    positive_df_full = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    c1_seqs = {s for _, s in read_fasta(C1_CLEAN_FASTA_V2_PATH)} if C1_CLEAN_FASTA_V2_PATH.exists() else set()
    c2_seqs = {s for _, s in read_fasta(C2_FASTA_PATH)} if C2_FASTA_PATH.exists() else set()
    screen_sequences = (
        set(positive_df_full["sequence"]) | set(conflict_df["sequence"]) | c1_seqs | c2_seqs
    )

    kept_candidates, _ = apply_secondary_blocklist(raw_candidates)
    seen_seqs: set[str] = set()
    candidate_records: list[tuple[str, str]] = []
    for header, sequence in kept_candidates:
        if sequence in screen_sequences or sequence in seen_seqs:
            continue
        if not is_valid_peptide(sequence, min_len=3, max_len=50):
            continue
        seen_seqs.add(sequence)
        candidate_records.append((header, sequence))

    candidate_id_map = {make_peptide_id(seq, prefix="C3"): seq for _, seq in candidate_records}

    positive_embeddings = _embed_via_wsl(
        training_df["peptide_id"].tolist(), training_df["sequence"].tolist(),
        C3_POSITIVE_EMBEDDINGS_CACHE, label="positives", force_cpu=force_cpu,
    )
    candidate_embeddings = _embed_via_wsl(
        list(candidate_id_map.keys()), list(candidate_id_map.values()),
        C3_CANDIDATE_EMBEDDINGS_CACHE, label="candidates", force_cpu=force_cpu,
    )

    centroids = compute_fold_centroids(positive_embeddings, fold_of, n_folds=n_folds)
    rankings = [rank_candidates_for_fold(candidate_embeddings, centroids[k], fold_id=k) for k in range(n_folds)]
    selections = select_top_n_per_fold(rankings, n=C3_TOP_N_PER_FOLD)

    ranking_rows = [
        {"fold_id": fold_id, "peptide_id": pid, "sequence": candidate_id_map[pid], "rank": rank, "cosine_similarity": sim}
        for fold_id, rows in selections.items()
        for pid, sim, rank in rows
    ]
    ranking_df = pd.DataFrame(ranking_rows)
    ranking_df.to_csv(C3_RANKING_PATH, index=False, lineterminator="\n")

    union_pids = sorted({row["peptide_id"] for row in ranking_rows})
    seen_union_seqs: set[str] = set()
    fasta_records = []
    for pid in union_pids:
        seq = candidate_id_map[pid]
        if seq not in seen_union_seqs:
            seen_union_seqs.add(seq)
            fasta_records.append((pid, seq))
    write_fasta(C3_FASTA_PATH, fasta_records)

    summary = {
        "n_candidate_universe_raw": len(raw_candidates),
        "n_candidate_universe_eligible": len(candidate_records),
        "n_folds": n_folds,
        "n_training_positives": len(positive_embeddings),
        "top_n_per_fold": C3_TOP_N_PER_FOLD,
        "n_union_records": len(fasta_records),
        "per_fold_n_selected": {k: len(v) for k, v in selections.items()},
        "screen_set_size": len(screen_sequences),
        "aodb_dfbp_biopep_screen": "NOT DONE -- AODB/DFBP/BIOPEP-UWM remain unintegrated project-wide; "
        "see IMPLEMENTATION_STATUS.md Known Issues.",
    }
    with open(C3_BUILD_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C3_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c3_hard_challenge_build",
            "raw_candidates": str(C3_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH), str(C1_CLEAN_FASTA_V2_PATH), str(C2_FASTA_PATH)],
            "summary": summary,
            "outputs": {
                "clean_fasta": str(C3_FASTA_PATH),
                "ranking": str(C3_RANKING_PATH),
                "report": str(C3_BUILD_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 2.4 resolution (Decisions A & B, approved 2026-10-14) -- versioned
# fixes for the two findings the audit surfaced. Neither overwrites the
# artifact it supersedes; both are new, separately versioned outputs.
C1_CLEAN_FASTA_V3_PATH = PROCESSED_DIR / "stage_c1_decoys_v3.fasta"
C1_ACCESSION_MAP_V3_PATH = PROCESSED_DIR / "c1_accession_map_v3.csv"
C1_CROSS_POOL_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_cross_pool_exclusion_log.csv"
C1_CROSS_POOL_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_cross_pool_replacement_log.csv"
C1_CROSS_POOL_FIX_REPORT_PATH = PROCESSED_DIR / "c1_cross_pool_fix_report.json"

C2_FASTA_V2_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled_v2.fasta"
C2_ACTIVITY_MAP_V2_PATH = PROCESSED_DIR / "c2_activity_map_v2.csv"
C2_CROSS_POOL_EXCLUSION_LOG_PATH = PROCESSED_DIR / "c2_cross_pool_exclusion_log.csv"
C2_CROSS_POOL_REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c2_cross_pool_replacement_log.csv"
C2_CROSS_POOL_FIX_REPORT_PATH = PROCESSED_DIR / "c2_cross_pool_fix_report.json"

# The one C2 sequence Decision B names explicitly -- a manually-reviewed,
# alignment-confirmed near-duplicate of an E1 FR1 positive (see
# IMPLEMENTATION_STATUS.md for the full EMBOSS needle alignment evidence).
# Deliberately NOT derived automatically from the CD-HIT cluster scan here:
# the instruction is explicit that cluster membership alone must not drive
# exclusion, so this is a named, reviewed constant, not a computed set.
C2_FLAGGED_HOMOLOGY_SEQUENCE = "LYQEPVLGPVRGPFP"


def run_fr2_c1_cross_pool_fix(seed: int = 42) -> dict:
    """Bucket 2.4 Decision A: remove the 8 sequences found to exactly
    overlap C2 from C1, replacing them 1:1 from the same UniProtKB
    candidate universe used by every prior C1 fix -- screened against FR1
    positives, the 179 conflicts, C2, AND C3 (the new requirement this
    fix exists to satisfy), so C3 never needs to be rebuilt as a side
    effect of this change.
    """
    if not C1_CLEAN_FASTA_V2_PATH.exists():
        raise FileNotFoundError(f"{C1_CLEAN_FASTA_V2_PATH} not found -- run fr2-c1-alphabet-fix first.")
    for p in (C1_RAW_CANDIDATES_PATH, POSITIVE_POOL_PATH, C2_FASTA_PATH, C3_FASTA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    c1_records = read_fasta(C1_CLEAN_FASTA_V2_PATH)
    c2_records = read_fasta(C2_FASTA_PATH)
    c3_records = read_fasta(C3_FASTA_PATH)
    candidate_pool_records = read_fasta(C1_RAW_CANDIDATES_PATH)
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)

    c1_seqs = {s for _, s in c1_records}
    c2_seqs = {s for _, s in c2_records}
    c3_seqs = {s for _, s in c3_records}
    exclude_sequences = c1_seqs & c2_seqs
    if not exclude_sequences:
        raise RuntimeError(
            "No C1/C2 exact overlap found -- this fix is a no-op on the current artifacts. "
            "Re-check whether Decision A still applies before running it."
        )

    screen_sequences = set(positive_df["sequence"]) | set(conflict_df["sequence"]) | c2_seqs | c3_seqs

    clean_records, exclusion_log, replacement_log, summary = clean_c1_cross_pool_overlap(
        c1_records, candidate_pool_records, exclude_sequences, screen_sequences, seed=seed
    )
    if summary["shortfall"] > 0:
        raise RuntimeError(
            f"Eligible replacement pool exhausted: needed {summary['n_replacements_needed']}, only "
            f"{summary['n_replacements_available']} available. Stopping rather than silently "
            "shipping a short pool -- see the project owner before changing source/criteria."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C1_CLEAN_FASTA_V3_PATH, clean_records)

    accession_map = pd.DataFrame(
        [
            {"peptide_header": h, "sequence": s, "length": len(s), **parse_uniprot_header(h)}
            for h, s in clean_records
        ]
    )
    accession_map.to_csv(C1_ACCESSION_MAP_V3_PATH, index=False, lineterminator="\n")
    pd.DataFrame(exclusion_log).to_csv(C1_CROSS_POOL_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")
    pd.DataFrame(replacement_log).to_csv(C1_CROSS_POOL_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    unique_seqs = {s for _, s in clean_records}
    summary.update(
        {
            "seed": seed,
            "n_unique_sequences": len(unique_seqs),
            "source_version": str(C1_CLEAN_FASTA_V2_PATH),
            "output_version": str(C1_CLEAN_FASTA_V3_PATH),
            "screened_against": ["FR1_positives", "conflicts_179", "C2", "C3_union"],
        }
    )
    with open(C1_CROSS_POOL_FIX_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C1_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c1_cross_pool_overlap_fix",
            "source_version": str(C1_CLEAN_FASTA_V2_PATH),
            "raw_candidates": str(C1_RAW_CANDIDATES_PATH),
            "screen_sources": [str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH), str(C2_FASTA_PATH), str(C3_FASTA_PATH)],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta_v3": str(C1_CLEAN_FASTA_V3_PATH),
                "accession_map_v3": str(C1_ACCESSION_MAP_V3_PATH),
                "exclusion_log": str(C1_CROSS_POOL_EXCLUSION_LOG_PATH),
                "replacement_log": str(C1_CROSS_POOL_REPLACEMENT_LOG_PATH),
                "report": str(C1_CROSS_POOL_FIX_REPORT_PATH),
            },
        },
    )
    return summary


def run_fr2_c2_cross_pool_fix(seed: int = 42) -> dict:
    """Bucket 2.4 Decision B: exclude the one C2 peptide manually confirmed
    (EMBOSS needle alignment, see IMPLEMENTATION_STATUS.md) to be a
    near-duplicate of an E1 FR1 positive, and replace it 1:1 from the same
    experimentally-reported Peptipedia tier Task 2.2 drew from -- screened
    against FR1 positives, the 179 conflicts, the remaining 1,999 C2
    sequences, the now-fixed C1 v3, AND C3.

    Must run AFTER ``run_fr2_c1_cross_pool_fix`` -- it screens against
    C1 v3, not v2, so this fix's replacement can never collide with
    Decision A's replacements either.
    """
    if not C2_FASTA_PATH.exists():
        raise FileNotFoundError(f"{C2_FASTA_PATH} not found -- run fr2-c2-build first.")
    if not C1_CLEAN_FASTA_V3_PATH.exists():
        raise FileNotFoundError(f"{C1_CLEAN_FASTA_V3_PATH} not found -- run fr2-c1-cross-pool-fix first.")
    for p in (C2_RAW_DUMP_PATH, POSITIVE_POOL_PATH, C3_FASTA_PATH, C2_ACTIVITY_MAP_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    c2_records = read_fasta(C2_FASTA_PATH)
    c2_seqs_current = {s for _, s in c2_records}
    if C2_FLAGGED_HOMOLOGY_SEQUENCE not in c2_seqs_current:
        raise RuntimeError(
            f"{C2_FLAGGED_HOMOLOGY_SEQUENCE!r} is not in the current C2 pool -- this fix is a "
            "no-op on the current artifacts. Re-check whether Decision B still applies."
        )

    activity_map_df = pd.read_csv(C2_ACTIVITY_MAP_PATH)
    flagged_row = activity_map_df[activity_map_df["sequence"] == C2_FLAGGED_HOMOLOGY_SEQUENCE].iloc[0]

    c1_v3_seqs = {s for _, s in read_fasta(C1_CLEAN_FASTA_V3_PATH)}
    c3_seqs = {s for _, s in read_fasta(C3_FASTA_PATH)}
    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    remaining_c2_seqs = c2_seqs_current - {C2_FLAGGED_HOMOLOGY_SEQUENCE}

    screen_sequences = (
        set(positive_df["sequence"])
        | set(conflict_df["sequence"])
        | remaining_c2_seqs
        | c1_v3_seqs
        | c3_seqs
    )

    activity_names = load_activity_names(C2_RAW_DUMP_PATH)
    sequences, activities = extract_c2_candidates(C2_RAW_DUMP_PATH)
    replacement_records, replacement_summary = build_c2_pool(
        sequences, activities, screen_sequences, n=1, seed=seed
    )
    if replacement_summary["shortfall"] > 0:
        raise RuntimeError(
            "No eligible replacement found for the excluded C2 sequence in the experimentally-"
            "reported Peptipedia tier under the expanded cross-pool screen. Stopping rather than "
            "silently shipping a short pool -- see the project owner before changing source/criteria."
        )

    new_record = replacement_records[0]
    new_peptide_id = make_peptide_id(new_record["sequence"], prefix="C2")

    clean_records = [(h, s) for h, s in c2_records if s != C2_FLAGGED_HOMOLOGY_SEQUENCE]
    clean_records.append((new_peptide_id, new_record["sequence"]))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta(C2_FASTA_V2_PATH, clean_records)

    new_activity_row = {
        "peptide_id": new_peptide_id,
        "id_peptide_peptipedia": new_record["id_peptide"],
        "sequence": new_record["sequence"],
        "length": new_record["length"],
        "activity_ids": ";".join(str(a) for a in new_record["activity_ids"]),
        "activity_names": ";".join(
            activity_names.get(a, f"unknown_activity_{a}") for a in new_record["activity_ids"]
        ),
        "has_experimental_evidence": new_record["has_experimental_evidence"],
    }
    updated_activity_map = pd.concat(
        [
            activity_map_df[activity_map_df["sequence"] != C2_FLAGGED_HOMOLOGY_SEQUENCE],
            pd.DataFrame([new_activity_row]),
        ],
        ignore_index=True,
    )
    updated_activity_map.to_csv(C2_ACTIVITY_MAP_V2_PATH, index=False, lineterminator="\n")

    exclusion_log = [
        {
            "peptide_id": flagged_row["peptide_id"],
            "sequence": C2_FLAGGED_HOMOLOGY_SEQUENCE,
            "reason": "homology_leakage_risk_to_fr1_e1_positive",
            "homologous_to_peptide_id": "AOP-032318CCA7",
            "homologous_to_sequence": "YQEPVLGPVRGPFPIIV",
            "homologous_to_evidence_tier": "E1",
            "alignment_tool": "EMBOSS needle (EBLOSUM62, gapopen=10, gapextend=0.5)",
            "alignment_identity_full_length_pct": 77.8,
            "alignment_identity_cdhit_shorter_seq_pct": 93.33,
            "alignment_gaps_pct": 22.2,
            "original_activity_names": flagged_row["activity_names"],
            "note": "Excluded as a conservative leakage-risk decision -- NOT claimed to be "
            "experimentally antioxidant-active. Original Peptipedia evidence preserved above.",
        }
    ]
    pd.DataFrame(exclusion_log).to_csv(C2_CROSS_POOL_EXCLUSION_LOG_PATH, index=False, lineterminator="\n")
    pd.DataFrame([new_activity_row]).to_csv(C2_CROSS_POOL_REPLACEMENT_LOG_PATH, index=False, lineterminator="\n")

    summary = {
        "source_version": str(C2_FASTA_PATH),
        "output_version": str(C2_FASTA_V2_PATH),
        "n_excluded": 1,
        "n_replaced": 1,
        "n_output_records": len(clean_records),
        "n_unique_sequences": len({s for _, s in clean_records}),
        "seed": seed,
        "screened_against": ["FR1_positives", "conflicts_179", "C2_remaining", "C1_v3", "C3_union"],
        "replacement_tier_summary": replacement_summary,
    }
    with open(C2_CROSS_POOL_FIX_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2)

    append_provenance_log(
        C2_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_c2_cross_pool_homology_fix",
            "source_version": str(C2_FASTA_PATH),
            "screen_sources": [
                str(POSITIVE_POOL_PATH), str(CONFLICT_LOG_PATH), str(C1_CLEAN_FASTA_V3_PATH), str(C3_FASTA_PATH),
            ],
            "seed": seed,
            "summary": summary,
            "outputs": {
                "clean_fasta_v2": str(C2_FASTA_V2_PATH),
                "activity_map_v2": str(C2_ACTIVITY_MAP_V2_PATH),
                "exclusion_log": str(C2_CROSS_POOL_EXCLUSION_LOG_PATH),
                "replacement_log": str(C2_CROSS_POOL_REPLACEMENT_LOG_PATH),
                "report": str(C2_CROSS_POOL_FIX_REPORT_PATH),
            },
        },
    )
    return summary


# Bucket 2.4 -- Pool Contamination and Leakage Audit.
BIOPEP_RAW_PATH = RAW_DIR / "BIOPEP-UWM" / "biopep_antioxidative.json"
BIOPEP_RAW_PROVENANCE_PATH = RAW_DIR / "BIOPEP-UWM" / "biopep_provenance.txt"

AUDIT_INTEGRITY_REPORT_PATH = PROCESSED_DIR / "audit_integrity_report.json"
AUDIT_OVERLAP_MATRIX_PATH = PROCESSED_DIR / "audit_exact_overlap_matrix.csv"
AUDIT_OVERLAP_DETAIL_PATH = PROCESSED_DIR / "audit_exact_overlap_detail.csv"
AUDIT_EXTERNAL_SCREEN_PATH = PROCESSED_DIR / "audit_external_aop_screen.json"
AUDIT_HOMOLOGY_CLUSTERS_PATH = PROCESSED_DIR / "audit_cross_pool_homology_clusters.csv"
AUDIT_HOMOLOGY_SUMMARY_PATH = PROCESSED_DIR / "audit_cross_pool_homology_summary.json"
AUDIT_C3_CONTRACT_REPORT_PATH = PROCESSED_DIR / "audit_c3_fold_contract_report.json"
AUDIT_REPORT_PATH = PROCESSED_DIR / "fr2_pool_audit_report.json"
AUDIT_PROVENANCE_LOG_PATH = PROCESSED_DIR / "fr2_pool_audit_provenance.jsonl"
AUDIT_CDHIT_OUTPUT_PREFIX = INTERIM_DIR / "audit_combined_pools_cdhit90"


def run_fr2_pool_audit() -> dict:
    """Bucket 2.4: formal, re-runnable contamination/leakage audit across
    FR1's positives, the 179 conflicts, and C1/C2/C3. Read-only with
    respect to every existing accepted artifact -- this stage never
    modifies pp1_baseline_v1 or any accepted C1/C2/C3 file; it only
    reports. See IMPLEMENTATION_STATUS.md for the full account of every
    finding and which ones are pending the project owner's decision.
    """
    if not POSITIVE_POOL_PATH.exists():
        raise FileNotFoundError(f"{POSITIVE_POOL_PATH} not found -- run fr1-positives first.")
    # Canonical C1/C2 sources as of the Bucket 2.4 Decision A/B resolution
    # (2026-10-14): v3/v2, not v2/v1 -- falls back to the pre-resolution
    # versions only if the fixes haven't been run yet in this checkout, so
    # this function stays usable mid-resolution, not just after it.
    c1_canonical_path = C1_CLEAN_FASTA_V3_PATH if C1_CLEAN_FASTA_V3_PATH.exists() else C1_CLEAN_FASTA_V2_PATH
    c2_canonical_path = C2_FASTA_V2_PATH if C2_FASTA_V2_PATH.exists() else C2_FASTA_PATH
    for p in (c1_canonical_path, c2_canonical_path, C3_FASTA_PATH):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found -- build C1/C2/C3 first.")

    positive_df = pd.read_parquet(POSITIVE_POOL_PATH)
    conflict_df = pd.read_csv(CONFLICT_LOG_PATH)
    external_control_df = pd.read_csv(PROCESSED_DIR / "anoxpepred_inactives_clean.csv")
    pos_records = list(zip(positive_df["peptide_id"], positive_df["sequence"]))
    conf_records = list(zip(conflict_df["peptide_id"], conflict_df["sequence"]))
    ext_records = list(zip(external_control_df["peptide_id"], external_control_df["sequence"]))
    c1_records = read_fasta(c1_canonical_path)
    c2_records = read_fasta(c2_canonical_path)
    c3_records = read_fasta(C3_FASTA_PATH)

    pool_records = {
        "FR1_positives": pos_records,
        "conflicts_179": conf_records,
        "external_control": ext_records,
        "C1_v3": c1_records,
        "C2_v2": c2_records,
        "C3_union": c3_records,
    }
    pool_seqs = {name: {s for _, s in recs} for name, recs in pool_records.items()}

    # --- Step 2: full sequence-integrity audit ---
    integrity_reports = [sequence_integrity_report(name, recs) for name, recs in pool_records.items()]
    with open(AUDIT_INTEGRITY_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(integrity_reports, handle, indent=2)

    overlap_matrix = pairwise_exact_overlap(pool_seqs)
    overlap_matrix.to_csv(AUDIT_OVERLAP_MATRIX_PATH, lineterminator="\n")

    names = list(pool_seqs.keys())
    detail_rows = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = overlap_detail(pool_seqs, a, b)
            for seq in shared:
                detail_rows.append({"pool_a": a, "pool_b": b, "sequence": seq, "length": len(seq)})
    pd.DataFrame(detail_rows, columns=["pool_a", "pool_b", "sequence", "length"]).to_csv(
        AUDIT_OVERLAP_DETAIL_PATH, index=False, lineterminator="\n"
    )

    # --- Step 3: external known-AOP screening ---
    RAW_DIR.joinpath("BIOPEP-UWM").mkdir(parents=True, exist_ok=True)
    if BIOPEP_RAW_PATH.exists():
        with open(BIOPEP_RAW_PATH, encoding="utf-8") as handle:
            biopep_records = json.load(handle)
    else:
        biopep_records = fetch_biopep_by_activity("antioxidative")
        with open(BIOPEP_RAW_PATH, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(biopep_records, handle, indent=2)
        with open(BIOPEP_RAW_PROVENANCE_PATH, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("BIOPEP-UWM Antioxidative Reference Set - Provenance Log\n")
            handle.write(f"Source: {BIOPEP_SEARCH_URL}?txt_search=antioxidative&menu_search=activity\n")
            handle.write("Access: open, no registration required\n")
            handle.write(f"Citation: {BIOPEP_CITATION}\n")
            handle.write(f"Records fetched: {len(biopep_records)}\n")

    biopep_seqs = {r["sequence"] for r in biopep_records if is_valid_peptide(r["sequence"], min_len=1, max_len=10_000)}
    external_hits = external_reference_screen(pool_seqs, biopep_seqs)
    external_screen_report = {
        "biopep_uwm": {
            "source": BIOPEP_SEARCH_URL,
            "citation": BIOPEP_CITATION,
            "n_reference_sequences_standard_alphabet": len(biopep_seqs),
            "hits_by_pool": {k: len(v) for k, v in external_hits.items()},
            "hit_sequences_by_pool": external_hits,
        },
        "aodb": {
            "status": "INACCESSIBLE",
            "evidence": "https://aodb.idruglab.cn returned HTTP 502 (Bad Gateway) from its own "
            "nginx and an expired TLS certificate, confirmed via direct curl with and without "
            "certificate verification. Not screened -- not a skipped check, a documented access "
            "failure at the time of this audit.",
        },
        "dfbp": {
            "status": "INACCESSIBLE",
            "evidence": "No working hosting URL could be found for DFBP (Qin et al. 2022, PubMed "
            "35552640) via web search or the PubMed record itself (blocked by a cookie wall in "
            "automated access). Not substituted with an unrelated database per instruction. Not "
            "screened -- a documented access failure, not a skipped check.",
        },
    }
    with open(AUDIT_EXTERNAL_SCREEN_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(external_screen_report, handle, indent=2)

    # --- Step 4: homology/leakage analysis beyond exact match ---
    homology_df, homology_summary = cross_pool_homology_clusters(
        pool_records, AUDIT_CDHIT_OUTPUT_PREFIX, identity=0.90, length_floor_for_interpretation=15
    )
    homology_df.to_csv(AUDIT_HOMOLOGY_CLUSTERS_PATH, index=False, lineterminator="\n")
    with open(AUDIT_HOMOLOGY_SUMMARY_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(homology_summary, handle, indent=2)

    # --- Step 5: validate the C3 fold-specific contract ---
    c3_contract_report: dict
    try:
        splits_df = pd.read_csv(GRAPHPART_SPLITS_PATH)
        fold_of = dict(zip(splits_df["AC"], splits_df["cluster"].astype(int)))
        ranking_df = pd.read_csv(C3_RANKING_PATH)
        fasta_ids = {h for h, _ in c3_records}
        if C3_POSITIVE_EMBEDDINGS_CACHE.exists():
            npz = np.load(C3_POSITIVE_EMBEDDINGS_CACHE, allow_pickle=False)
            positive_embeddings = {pid: npz["embeddings"][i] for i, pid in enumerate(npz["peptide_ids"])}
            c3_contract_report = validate_c3_fold_contract(
                positive_embeddings, fold_of, ranking_df, fasta_ids, top_n_per_fold=C3_TOP_N_PER_FOLD
            )
        else:
            c3_contract_report = {
                "fold_safety_verified": None,
                "reason": f"{C3_POSITIVE_EMBEDDINGS_CACHE} not present locally (gitignored cache) -- "
                "re-run fr2-c3-build to regenerate it before this check can re-verify fold-safety "
                "against the real embeddings.",
            }
    except AssertionError as exc:
        c3_contract_report = {"fold_safety_verified": False, "violation": str(exc)}
    with open(AUDIT_C3_CONTRACT_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(c3_contract_report, handle, indent=2)

    # --- assemble top-level summary ---
    c1_c2_overlap = overlap_detail(pool_seqs, "C1_v3", "C2_v2")
    decision_a_resolved = len(c1_c2_overlap) == 0 and C1_CLEAN_FASTA_V3_PATH.exists()
    decision_b_resolved = C2_FLAGGED_HOMOLOGY_SEQUENCE not in pool_seqs["C2_v2"] and C2_FASTA_V2_PATH.exists()

    findings: dict = {}
    if not decision_a_resolved:
        findings["c1_c2_exact_overlap"] = {
            "status": "PENDING",
            "n_sequences": len(c1_c2_overlap),
            "sequences": c1_c2_overlap,
            "proposed_correction": "Pending project-owner decision -- NOT applied.",
        }
    if not decision_b_resolved:
        findings["c2_homology_to_fr1_positive"] = {
            "status": "PENDING",
            "example_sequence": C2_FLAGGED_HOMOLOGY_SEQUENCE,
            "proposed_correction": "Pending project-owner decision -- NOT applied.",
        }
    resolution_notes = {
        "decision_a_c1_c2_exact_overlap": "RESOLVED 2026-10-14 (see c1_cross_pool_fix_report.json) -- "
        "8 sequences removed from C1 (kept in C2, per approved 'preserve C2's biological-annotation "
        "precedence'), replaced 1:1 from the UniProtKB candidate universe, screened against FR1 "
        "positives, 179 conflicts, C2, and C3. Canonical C1 artifact is now stage_c1_decoys_v3.fasta."
        if decision_a_resolved
        else "NOT YET RESOLVED -- run fr2-c1-cross-pool-fix.",
        "decision_b_c2_homology_to_e1_positive": "RESOLVED 2026-10-14 (see c2_cross_pool_fix_report.json) "
        "-- C2-EFDBC5460B ('LYQEPVLGPVRGPFP') excluded as a conservative leakage-risk decision (NOT "
        "claimed experimentally inactive), replaced 1:1 from the experimentally-reported Peptipedia "
        "tier, screened against FR1 positives, 179 conflicts, remaining C2, C1 v3, and C3. Canonical "
        "C2 artifact is now stage_c2_bioactive_unlabeled_v2.fasta."
        if decision_b_resolved
        else "NOT YET RESOLVED -- run fr2-c2-cross-pool-fix.",
        "additional_homology_candidates": "Of the 14 other candidates found alongside the "
        "project-owner-flagged C2/FR1-positive pair, reviewed individually (not auto-excluded by "
        "cluster membership): 3 were fully resolved as a side effect of Decision A (their shared "
        "member was one of the 8 exact C1/C2 duplicates, now removed from C1); "
        f"{homology_summary['n_cross_pool_clusters_real_homology_candidates']} remain as near-"
        "duplicate (not exact) C1<->C2 pairs post-fix. All are C1<->C2 only (no FR1-positive "
        "involvement) and from peptide families with no plausible antioxidant mechanism "
        "(ribosomal/zinc-ribbon proteins, protamine-like and homeodomain cell-penetrating peptides, "
        "actin/gliadin fragments, cysteine-rich defensin-like peptides) -- assessed as redundant "
        "construction overlap between two unlabeled pools, not a label-leakage risk, since neither "
        "pool carries ground truth. Recommendation: accept and document as a known, bounded "
        "limitation (same treatment as C1's intentional record-level duplicates) rather than a "
        "further exclude-and-replace cycle. See audit_cross_pool_homology_clusters.csv for the full "
        "per-cluster evidence; revisit if the project owner wants a stricter policy.",
    }

    summary = {
        "integrity_reports": integrity_reports,
        "exact_overlap_nonzero_pairs": [
            {"pool_a": r["pool_a"], "pool_b": r["pool_b"], "sequence": r["sequence"]}
            for r in detail_rows
        ],
        "contamination_requiring_decision": findings,
        "bucket_2_4_resolution_status": resolution_notes,
        "external_screen": {k: v for k, v in external_screen_report.items()},
        "homology_summary": homology_summary,
        "c3_fold_contract": c3_contract_report,
        "known_incomplete_checks": [
            "AODB screening -- server inaccessible (HTTP 502 + expired TLS cert) at audit time.",
            "DFBP screening -- no discoverable hosting URL.",
        ],
        "accepted_methodological_limitations": [
            "CD-HIT percent-identity is not biologically interpretable for pairs where the shorter "
            "sequence is <15 AA (chance substring matches dominate at this length); such clusters "
            "are reported for transparency but excluded from the 'real homology candidate' count.",
            "C1 retains natural duplicate sequences by design (record-vs-unique-sequence distinction, "
            "confirmed 2026-10-14) -- any future train/val/test split MUST group identical sequences "
            "together to avoid sequence-level leakage; this is a loader-design requirement, not "
            "something this audit can enforce by itself.",
            "C3's 25,000-candidate UniRef50 universe is a deterministic ID-sorted slice of the "
            "870,941-cluster population in its length window, not a random sample -- a potential "
            "coverage bias to examine under Task 2.5, not evidence the pool is invalid.",
            "2 external-control ('experimentally inactive') peptides independently hit BIOPEP-UWM's "
            "antioxidative reference set -- the same cross-database annotation conflict phenomenon "
            "already documented for the 179 FR1 conflicts; preserved as a documented uncertainty, not "
            "acted on.",
        ],
        "ready_for_technical_acceptance": decision_a_resolved and decision_b_resolved,
    }
    with open(AUDIT_REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, default=str)

    append_provenance_log(
        AUDIT_PROVENANCE_LOG_PATH,
        {
            "stage": "fr2_pool_contamination_leakage_audit",
            "pools_audited": list(pool_records.keys()),
            "outputs": {
                "integrity": str(AUDIT_INTEGRITY_REPORT_PATH),
                "overlap_matrix": str(AUDIT_OVERLAP_MATRIX_PATH),
                "overlap_detail": str(AUDIT_OVERLAP_DETAIL_PATH),
                "external_screen": str(AUDIT_EXTERNAL_SCREEN_PATH),
                "homology_clusters": str(AUDIT_HOMOLOGY_CLUSTERS_PATH),
                "homology_summary": str(AUDIT_HOMOLOGY_SUMMARY_PATH),
                "c3_contract": str(AUDIT_C3_CONTRACT_REPORT_PATH),
                "report": str(AUDIT_REPORT_PATH),
            },
        },
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PU-AOP (Component 02) CLI")
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("fr1-positives", help="Build the conflict-resolved FR1 positive pool")
    sub.add_parser("fr1-cluster", help="CD-HIT 90% identity clustering (Bucket 1.5)")
    sub.add_parser("fr1-split", help="GraphPart 40% identity 5-fold split (Bucket 1.6)")
    sub.add_parser("fr1-freeze", help="Snapshot validated FR1 artifacts as a versioned baseline (Bucket 1.7)")
    sub.add_parser("fr2-c1-clean", help="Resolve C1/positive-pool leakage (Bucket 2.1 close-out)")
    sub.add_parser(
        "fr2-c1-alphabet-fix",
        help="Enforce standard-20-AA-alphabet policy on C1, versioned as v2 (Bucket 2.1 follow-up)",
    )
    sub.add_parser("fr2-c2-build", help="Build the C2 bioactive-unlabeled pool from Peptipedia (Bucket 2.2)")
    sub.add_parser("fr2-c3-fetch-candidates", help="Fetch the UniRef50 candidate universe (Bucket 2.3 step 1)")
    sub.add_parser("fr2-c3-build", help="Fold-safe ESM-2 hard-challenge selection (Bucket 2.3 step 2)")
    sub.add_parser("fr2-pool-audit", help="Pool contamination and leakage audit (Bucket 2.4)")
    sub.add_parser("fr2-c1-cross-pool-fix", help="Decision A: remove C1/C2 exact overlap (Bucket 2.4 resolution)")
    sub.add_parser("fr2-c2-cross-pool-fix", help="Decision B: exclude C2 homolog of an E1 positive (Bucket 2.4 resolution)")
    sub.add_parser("esm2-smoketest", help="ESM-2 embedding interface smoke test (Bucket 3.2)")
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
    if args.stage == "fr2-c1-clean":
        summary = run_fr2_c1_clean()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c1-alphabet-fix":
        summary = run_fr2_c1_alphabet_fix()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c2-build":
        summary = run_fr2_c2_build()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c3-fetch-candidates":
        summary = run_fr2_c3_fetch_candidates()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c3-build":
        summary = run_fr2_c3_build()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c1-cross-pool-fix":
        summary = run_fr2_c1_cross_pool_fix()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-c2-cross-pool-fix":
        summary = run_fr2_c2_cross_pool_fix()
        print(json.dumps(summary, indent=2))
        return 0
    if args.stage == "fr2-pool-audit":
        summary = run_fr2_pool_audit()
        print(json.dumps({k: v for k, v in summary.items() if k != "integrity_reports"}, indent=2, default=str))
        return 0
    if args.stage == "esm2-smoketest":
        report = run_esm2_smoke_test()
        print(json.dumps({k: v for k, v in report.items() if k != "per_peptide"}, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
