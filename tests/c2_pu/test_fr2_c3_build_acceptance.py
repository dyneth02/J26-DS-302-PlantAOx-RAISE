"""FR2 Bucket 2.3 acceptance checks against the real, full C3 artifacts (not
a sample). Skips cleanly if the UniRef50 raw candidates or the built pool
aren't present locally. The fold-safety property itself is unit-tested in
test_c3.py against synthetic data; these checks validate that the real
build's *outputs* are structurally consistent with that guarantee (every
fold has its own ranking rows, no fold exceeds the requested top-N) plus
the usual full-file leakage/alphabet/reproducibility checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.common.sequence import is_standard_alphabet
from plantaox.c2_pu.run import C3_RAW_CANDIDATES_PATH, C3_TOP_N_PER_FOLD, run_fr2_c3_build

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

C3_FASTA_PATH = PROCESSED_DIR / "stage_c3_esm2_hard_challenges.fasta"
C3_RANKING_PATH = PROCESSED_DIR / "c3_similarity_ranking.csv"
C3_BUILD_REPORT_PATH = PROCESSED_DIR / "c3_build_report.json"
POSITIVE_POOL_PATH = PROCESSED_DIR / "aop_positives_provisional.parquet"
CONFLICT_LOG_PATH = REPO_ROOT / "data" / "interim" / "c2_pu" / "label_conflicts_anox_vs_multiaop.csv"
C1_FASTA_V2_PATH = PROCESSED_DIR / "stage_c1_decoys_v2.fasta"
C2_FASTA_PATH = PROCESSED_DIR / "stage_c2_bioactive_unlabeled.fasta"

pytestmark = pytest.mark.skipif(
    not C3_FASTA_PATH.exists(), reason="FR2 C3 hard-challenge pool not present in this checkout"
)


def test_c3_pool_is_standard_alphabet_and_in_length_window():
    records = read_fasta(C3_FASTA_PATH)
    assert len(records) > 0
    assert all(is_standard_alphabet(s) for _, s in records)
    lengths = [len(s) for _, s in records]
    assert min(lengths) >= 3
    assert max(lengths) <= 50


def test_c3_pool_is_the_deduplicated_union_of_the_ranking_csv():
    records = read_fasta(C3_FASTA_PATH)
    ranking_df = pd.read_csv(C3_RANKING_PATH)
    assert set(s for _, s in records) == set(ranking_df["sequence"])
    assert len({h for h, _ in records}) == len(records)  # peptide IDs unique in the FASTA


def test_every_fold_has_its_own_ranking_rows_never_exceeding_top_n():
    ranking_df = pd.read_csv(C3_RANKING_PATH)
    report = json.loads(C3_BUILD_REPORT_PATH.read_text())
    n_folds = report["n_folds"]
    assert set(ranking_df["fold_id"].unique()) == set(range(n_folds))
    for fold_id in range(n_folds):
        fold_rows = ranking_df[ranking_df["fold_id"] == fold_id]
        assert len(fold_rows) <= C3_TOP_N_PER_FOLD
        assert fold_rows["rank"].min() == 1
        assert fold_rows["rank"].is_unique


def test_each_folds_ranking_is_sorted_by_descending_similarity():
    ranking_df = pd.read_csv(C3_RANKING_PATH)
    for fold_id, group in ranking_df.groupby("fold_id"):
        sims = group.sort_values("rank")["cosine_similarity"].tolist()
        assert sims == sorted(sims, reverse=True)


def test_c3_pool_has_zero_overlap_with_positives_conflicts_c1_c2():
    seqs = {s for _, s in read_fasta(C3_FASTA_PATH)}
    screen = set(pd.read_parquet(POSITIVE_POOL_PATH)["sequence"]) | set(
        pd.read_csv(CONFLICT_LOG_PATH)["sequence"]
    )
    if C1_FASTA_V2_PATH.exists():
        screen |= {s for _, s in read_fasta(C1_FASTA_V2_PATH)}
    if C2_FASTA_PATH.exists():
        screen |= {s for _, s in read_fasta(C2_FASTA_PATH)}
    assert seqs.isdisjoint(screen)


def test_build_report_is_internally_consistent():
    report = json.loads(C3_BUILD_REPORT_PATH.read_text())
    ranking_df = pd.read_csv(C3_RANKING_PATH)
    records = read_fasta(C3_FASTA_PATH)
    assert report["n_union_records"] == len(records)
    assert sum(report["per_fold_n_selected"].values()) == len(ranking_df)


@pytest.mark.skipif(not C3_RAW_CANDIDATES_PATH.exists(), reason="UniRef50 raw candidates not present locally")
def test_rerunning_c3_build_is_reproducible():
    import hashlib

    def file_hash(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = {p: file_hash(p) for p in [C3_FASTA_PATH, C3_RANKING_PATH]}
    run_fr2_c3_build()
    after = {p: file_hash(p) for p in before}
    for p in before:
        assert before[p] == after[p], f"{p.name} changed across a reproducibility re-run"
