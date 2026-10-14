"""Tests for pools.py (FR2 Bucket 2.1 — C1 blocklist, sampling, leakage cleanup)."""

from __future__ import annotations

from plantaox.c2_pu.pools import (
    BIOACTIVITY_KEYWORDS,
    apply_secondary_blocklist,
    clean_c1_pool,
    find_contamination,
    matches_bioactivity_blocklist,
    parse_uniprot_header,
    sample_c1_decoys,
    select_replacements,
)


def test_blocklist_is_lowercased():
    assert all(kw == kw.lower() for kw in BIOACTIVITY_KEYWORDS)


def test_matches_bioactivity_blocklist_case_insensitive():
    assert matches_bioactivity_blocklist("sp|X|Y Some ANTIOXIDANT peptide")
    assert matches_bioactivity_blocklist("sp|X|Y Some antioxidant peptide")
    assert not matches_bioactivity_blocklist("sp|X|Y Totally unrelated ribosomal protein")


def test_apply_secondary_blocklist_splits_correctly():
    candidates = [
        ("sp|A|A Ribosomal protein L36", "MKRT"),
        ("sp|B|B Defensin NsD7", "KPEE"),
        ("sp|C|C Uncharacterized protein", "GGGQ"),
    ]
    kept, excluded = apply_secondary_blocklist(candidates)
    assert kept == [("sp|A|A Ribosomal protein L36", "MKRT"), ("sp|C|C Uncharacterized protein", "GGGQ")]
    assert excluded == [("sp|B|B Defensin NsD7", "KPEE")]


def test_sample_c1_decoys_is_deterministic():
    candidates = [(f"sp|{i}|X", f"SEQ{i}") for i in range(100)]
    a = sample_c1_decoys(candidates, n=10, seed=42)
    b = sample_c1_decoys(candidates, n=10, seed=42)
    assert a == b
    c = sample_c1_decoys(candidates, n=10, seed=7)
    assert a != c


def test_find_contamination():
    c1 = [("a", "AAAA"), ("b", "BBBB"), ("c", "CCCC")]
    found = find_contamination(c1, {"BBBB", "ZZZZ"})
    assert found == [("b", "BBBB")]


def test_select_replacements_deterministic_and_disjoint_from_exhaustion():
    candidates = [(f"sp|{i}|X", f"SEQ{i}") for i in range(20)]
    reps = select_replacements(candidates, 3, seed=42)
    assert len(reps) == 3
    assert len(set(reps)) == 3  # no duplicates
    reps2 = select_replacements(candidates, 3, seed=42)
    assert reps == reps2


def test_parse_uniprot_header_standard_format():
    header = "sp|Q10582|ANGT2_BOTJA Angiotensin-like peptide 2 (Fragment) OS=Bothrops jararaca OX=8724 PE=1 SV=1"
    parsed = parse_uniprot_header(header)
    assert parsed["db"] == "sp"
    assert parsed["accession"] == "Q10582"
    assert parsed["entry_name"] == "ANGT2_BOTJA"
    assert parsed["organism"] == "Bothrops jararaca"
    assert parsed["is_fragment"] is True
    assert "Angiotensin-like peptide 2" in parsed["description"]


def test_parse_uniprot_header_non_fragment():
    header = "sp|A5A616|MGTS_ECOLI Small protein MgtS OS=Escherichia coli (strain K12) OX=83333 GN=mgtS PE=1 SV=1"
    parsed = parse_uniprot_header(header)
    assert parsed["is_fragment"] is False
    assert parsed["organism"] == "Escherichia coli (strain K12)"


def test_parse_uniprot_header_malformed_falls_back_gracefully():
    parsed = parse_uniprot_header("not a uniprot header at all")
    assert parsed["accession"] is None
    assert parsed["is_fragment"] is False


def test_clean_c1_pool_removes_contamination_and_fills_from_candidates():
    c1 = [
        ("sp|KEEP1|X desc1", "KEEP1SEQ"),
        ("sp|CONTAM|X Angiotensin-like peptide", "DRVYIHPF"),  # contaminated
        ("sp|KEEP2|X desc2", "KEEP2SEQ"),
    ]
    candidate_pool = [
        ("sp|KEEP1|X desc1", "KEEP1SEQ"),  # already in c1, not eligible
        ("sp|BAD|X some toxin peptide", "TOXINSEQ"),  # blocklisted, not eligible
        ("sp|REPL|X fresh candidate", "FRESHSEQ"),  # eligible replacement
        ("sp|ALSO_POS|X desc", "OTHERPOSITIVE"),  # in screen set, not eligible
    ]
    screen = {"DRVYIHPF", "OTHERPOSITIVE"}

    clean, exclusion_log, replacement_log, summary = clean_c1_pool(c1, candidate_pool, screen, seed=42)

    assert summary["n_input_records"] == 3
    assert summary["n_contaminated_removed"] == 1
    assert summary["n_replacements_needed"] == 1
    assert summary["n_replacements_made"] == 1
    assert summary["shortfall"] == 0
    assert summary["n_output_records"] == 3

    clean_seqs = {s for _, s in clean}
    assert "DRVYIHPF" not in clean_seqs
    assert "KEEP1SEQ" in clean_seqs and "KEEP2SEQ" in clean_seqs
    assert "FRESHSEQ" in clean_seqs  # the only eligible candidate got picked

    assert len(exclusion_log) == 1
    assert exclusion_log[0]["sequence"] == "DRVYIHPF"
    assert exclusion_log[0]["accession"] == "CONTAM"

    assert len(replacement_log) == 1
    assert replacement_log[0]["sequence"] == "FRESHSEQ"


def test_clean_c1_pool_reports_shortfall_without_crashing_when_no_eligible_candidates():
    c1 = [("sp|CONTAM|X", "BADSEQ")]
    candidate_pool: list[tuple[str, str]] = []  # nothing eligible
    clean, exclusion_log, replacement_log, summary = clean_c1_pool(c1, candidate_pool, {"BADSEQ"}, seed=42)

    assert summary["n_contaminated_removed"] == 1
    assert summary["n_replacements_made"] == 0
    assert summary["shortfall"] == 1
    assert summary["n_output_records"] == 0
    assert clean == []
    assert replacement_log == []
