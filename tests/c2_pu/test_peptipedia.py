"""Tests for curation/peptipedia.py (Bucket 2.2 -- C2 bioactive unlabeled
pool), against small synthetic pg_dump-format fixtures, not the real 281MB
Zenodo dump (that's covered separately by a skip-if-absent acceptance test).
"""

from __future__ import annotations

import gzip

from plantaox.c2_pu.curation.peptipedia import (
    ANTIOXIDANT_ACTIVITY_ID,
    build_c2_pool,
    extract_c2_candidates,
    iter_copy_rows,
    load_activity_names,
)

assert ANTIOXIDANT_ACTIVITY_ID == 41


def _write_fixture_dump(path, peptide_rows, activity_rows, activity_def_rows):
    def line(fields):
        return "\t".join("\\N" if f is None else str(f) for f in fields) + "\n"

    text = (
        "COPY public.activity (id_activity, name, description, id_parent) FROM stdin;\n"
        + "".join(line(r) for r in activity_def_rows)
        + "\\.\n"
        "COPY public.peptide (id_peptide, sequence, is_canon, swissprot_id, nutraceutical, "
        "act_date, length, molecular_weight, isoelectric_point, charge_density, charge, "
        "instability_index, aromaticity, aliphatic_index, boman_index, hydrophobic_ratio, "
        "keyword, patent, reference, half_life) FROM stdin;\n"
        + "".join(line(r) for r in peptide_rows)
        + "\\.\n"
        "COPY public.peptide_has_activity (id_peptide, id_activity, predicted) FROM stdin;\n"
        + "".join(line(r) for r in activity_rows)
        + "\\.\n"
    )
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def test_iter_copy_rows_parses_tab_delimited_block_and_unescapes_null(tmp_path):
    dump_path = tmp_path / "fixture.sql.gz"
    _write_fixture_dump(
        dump_path,
        peptide_rows=[[1, "ACDEFG", "t"] + [None] * 17],
        activity_rows=[[1, 2, "f"]],
        activity_def_rows=[[2, "Antimicrobial", None, None]],
    )
    peptide_rows = list(iter_copy_rows(dump_path, "peptide"))
    assert len(peptide_rows) == 1
    assert peptide_rows[0][0] == "1"
    assert peptide_rows[0][1] == "ACDEFG"
    assert peptide_rows[0][3] is None  # swissprot_id column, \N unescaped to None


def test_load_activity_names(tmp_path):
    dump_path = tmp_path / "fixture.sql.gz"
    _write_fixture_dump(
        dump_path,
        peptide_rows=[],
        activity_rows=[],
        activity_def_rows=[[2, "Antimicrobial", "desc", None], [41, "Anti oxidative", "desc", 1]],
    )
    names = load_activity_names(dump_path)
    assert names[2] == "Antimicrobial"
    assert names[41] == "Anti oxidative"


def test_extract_c2_candidates_applies_length_and_alphabet_window(tmp_path):
    dump_path = tmp_path / "fixture.sql.gz"
    _write_fixture_dump(
        dump_path,
        peptide_rows=[
            [1, "ACDEFG", "t"] + [None] * 17,  # standard, in window -- kept
            [2, "AC", "t"] + [None] * 17,  # too short (<3) -- dropped
            [3, "ACXEFG", "t"] + [None] * 17,  # non-standard residue -- dropped
            [4, "A" * 60, "t"] + [None] * 17,  # too long (>50) -- dropped
        ],
        activity_rows=[[1, 2, "f"], [2, 2, "f"], [3, 2, "f"], [4, 2, "f"]],
        activity_def_rows=[[2, "Antimicrobial", None, None]],
    )
    sequences, activities = extract_c2_candidates(dump_path)
    assert sequences == {1: "ACDEFG"}
    assert activities == {1: [(2, False)]}


def test_build_c2_pool_excludes_antioxidant_tagged_peptides():
    sequences = {1: "ACDEFG", 2: "GHIKLM", 3: "MNPQRS"}
    activities = {
        1: [(2, False)],  # antimicrobial, experimental -- eligible
        2: [(41, False)],  # antioxidant -- must be excluded regardless of tier
        3: [(2, True), (41, True)],  # also antioxidant-tagged -- excluded
    }
    records, summary = build_c2_pool(sequences, activities, screen_sequences=set(), n=10, seed=42)
    seqs = {r["sequence"] for r in records}
    assert seqs == {"ACDEFG"}
    assert summary["n_total_eligible_unique_sequences"] == 1


def test_build_c2_pool_excludes_screened_positive_and_conflict_sequences():
    sequences = {1: "ACDEFG", 2: "GHIKLM"}
    activities = {1: [(2, False)], 2: [(2, False)]}
    records, summary = build_c2_pool(sequences, activities, screen_sequences={"GHIKLM"}, n=10, seed=42)
    assert [r["sequence"] for r in records] == ["ACDEFG"]


def test_build_c2_pool_dedupes_by_sequence_keeping_lowest_id():
    sequences = {5: "ACDEFG", 2: "ACDEFG"}  # same sequence, two Peptipedia ids
    activities = {5: [(2, False)], 2: [(2, False)]}
    records, _ = build_c2_pool(sequences, activities, screen_sequences=set(), n=10, seed=42)
    assert len(records) == 1
    assert records[0]["id_peptide"] == 2


def test_build_c2_pool_prefers_experimental_tier_and_falls_back_to_predicted():
    # 2 experimental-evidence peptides, 1 predicted-only; ask for all 3.
    sequences = {1: "AAAAAA", 2: "CCCCCC", 3: "DDDDDD"}
    activities = {
        1: [(2, False)],
        2: [(2, False)],
        3: [(2, True)],  # predicted only
    }
    records, summary = build_c2_pool(sequences, activities, screen_sequences=set(), n=3, seed=42)
    assert summary["n_experimental_tier"] == 2
    assert summary["n_predicted_only_tier"] == 1
    assert summary["n_sampled_from_experimental"] == 2
    assert summary["n_sampled_from_predicted_only"] == 1
    assert summary["shortfall"] == 0


def test_build_c2_pool_reports_shortfall_without_crashing():
    sequences = {1: "AAAAAA"}
    activities = {1: [(2, False)]}
    records, summary = build_c2_pool(sequences, activities, screen_sequences=set(), n=5, seed=42)
    assert len(records) == 1
    assert summary["shortfall"] == 4


def test_build_c2_pool_is_deterministic():
    amino_acids = "ACDEFGHIKLMNPQRSTVWY"
    sequences = {
        i: amino_acids[i % 20] + amino_acids[(i // 20) % 20] + amino_acids[(i // 400) % 20]
        for i in range(1, 51)
    }
    assert len(set(sequences.values())) == 50  # fixture sanity check, not production logic
    activities = {i: [(2, False)] for i in sequences}
    records_a, _ = build_c2_pool(sequences, activities, screen_sequences=set(), n=10, seed=42)
    records_b, _ = build_c2_pool(sequences, activities, screen_sequences=set(), n=10, seed=42)
    assert [r["id_peptide"] for r in records_a] == [r["id_peptide"] for r in records_b]
