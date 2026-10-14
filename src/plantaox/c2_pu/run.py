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
from plantaox.c2_pu.common.sequence import make_peptide_id
from plantaox.c2_pu.pools import clean_c1_alphabet, clean_c1_pool, parse_uniprot_header

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
    if args.stage == "esm2-smoketest":
        report = run_esm2_smoke_test()
        print(json.dumps({k: v for k, v in report.items() if k != "per_peptide"}, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
