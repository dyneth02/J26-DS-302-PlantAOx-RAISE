"""FR2 Bucket 2.1 close-out acceptance checks against the real, full
cleaned C1 artifact (not a sample). Skips cleanly if not present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.pools import apply_secondary_blocklist, sample_c1_decoys
from plantaox.c2_pu.run import run_fr2_c1_clean

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw" / "c2_pu" / "UniProt_decoys"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

CLEAN_FASTA_PATH = PROCESSED_DIR / "stage_c1_decoys.fasta"
RAW_DECOYS_PATH = RAW_DIR / "stage_c1_decoys.fasta"
EXCLUSION_LOG_PATH = PROCESSED_DIR / "c1_leakage_exclusion_log.csv"
REPLACEMENT_LOG_PATH = PROCESSED_DIR / "c1_leakage_replacement_log.csv"
ACCESSION_MAP_PATH = PROCESSED_DIR / "c1_accession_map.csv"
CLEAN_REPORT_PATH = PROCESSED_DIR / "c1_clean_report.json"
POSITIVE_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CONFLICT_LOG_PATH = REPO_ROOT / "data" / "interim" / "c2_pu" / "label_conflicts_anox_vs_multiaop.csv"

pytestmark = pytest.mark.skipif(
    not CLEAN_FASTA_PATH.exists(), reason="FR2 C1 clean pool not present in this checkout"
)


def test_original_construction_is_reproducible_from_scratch():
    # Bucket 2.1's own checklist: "re-run the full pipeline once from scratch
    # with the same seed and diff against the saved file." The query-level
    # candidate universe (uniprotkb_candidates.fasta) plus the documented
    # secondary blocklist plus seed 42 should reproduce the raw,
    # historical-evidence file exactly -- not just the cleaned one.
    candidates = read_fasta(RAW_DIR / "uniprotkb_candidates.fasta")
    kept, excluded = apply_secondary_blocklist(candidates)
    assert len(kept) == 8233  # documented in stage_c1_provenance.txt
    assert len(excluded) == 597

    reproduced = set(sample_c1_decoys(kept, n=5000, seed=42))
    actual = set(read_fasta(RAW_DECOYS_PATH))
    assert reproduced == actual


def test_raw_file_untouched_as_historical_evidence():
    # The raw file must still contain the known-contaminated sequence -- if
    # this ever fails, someone edited supposedly-immutable raw data in place.
    raw_seqs = {s for _, s in read_fasta(RAW_DECOYS_PATH)}
    assert "DRVYIHPF" in raw_seqs


def test_clean_pool_has_zero_contamination_against_positives_and_conflicts():
    clean_seqs = {s for _, s in read_fasta(CLEAN_FASTA_PATH)}
    screen = set(pd.read_parquet(POSITIVE_POOL_PATH)["sequence"]) | set(
        pd.read_csv(CONFLICT_LOG_PATH)["sequence"]
    )
    assert clean_seqs.isdisjoint(screen)


def test_clean_pool_record_count_and_length_window():
    records = read_fasta(CLEAN_FASTA_PATH)
    assert len(records) == 5000
    lengths = [len(s) for _, s in records]
    assert min(lengths) >= 3
    assert max(lengths) <= 50


def test_exclusion_and_replacement_logs_are_consistent_with_the_report():
    report = json.loads(CLEAN_REPORT_PATH.read_text())
    exclusion_df = pd.read_csv(EXCLUSION_LOG_PATH)
    replacement_df = pd.read_csv(REPLACEMENT_LOG_PATH)
    assert len(exclusion_df) == report["n_contaminated_removed"]
    assert len(replacement_df) == report["n_replacements_made"]
    assert report["shortfall"] == 0


def test_accession_map_covers_every_record_with_no_duplicates():
    records = read_fasta(CLEAN_FASTA_PATH)
    accession_map = pd.read_csv(ACCESSION_MAP_PATH)
    assert len(accession_map) == len(records)
    assert set(accession_map["sequence"]) == {s for _, s in records}


def test_rerunning_c1_clean_is_reproducible():
    import hashlib

    def file_hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = {
        p: file_hash(p)
        for p in [CLEAN_FASTA_PATH, EXCLUSION_LOG_PATH, REPLACEMENT_LOG_PATH, ACCESSION_MAP_PATH]
    }
    run_fr2_c1_clean()
    after = {p: file_hash(p) for p in before}
    for p in before:
        assert before[p] == after[p], f"{p.name} changed across a reproducibility re-run"
