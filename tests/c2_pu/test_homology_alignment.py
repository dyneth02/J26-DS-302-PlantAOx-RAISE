"""Tests for curation/homology_alignment.py's needleall pair-format parser,
against a small fixed sample of real needleall output (captured once from
an actual WSL run, not hand-written, so the regex is validated against the
tool's real formatting quirks)."""

from __future__ import annotations

from pathlib import Path

from plantaox.c2_pu.curation.homology_alignment import parse_needleall_pairs, run_needleall

_SAMPLE_OUTPUT = """########################################
# Program: needleall
# Rundate: Wed 14 Oct 2026 10:07:00
# Commandline: needleall
#    -asequence "a.fasta"
#    -bsequence "b.fasta"
# Align_format: pair
########################################

#=======================================
#
# Aligned_sequences: 2
# 1: seqA1
# 2: seqB1
# Matrix: EBLOSUM62
# Gap_penalty: 10.0
# Extend_penalty: 0.5
#
# Length: 3
# Identity:       2/3 (66.7%)
# Similarity:     2/3 (66.7%)
# Gaps:           0/3 ( 0.0%)
# Score: 15.0
#
#
#=======================================

seqA1              1 RWK      3
                     ||.
seqB1              1 RWM      3


#=======================================
#
# Aligned_sequences: 2
# 1: seqA2
# 2: seqB2
# Matrix: EBLOSUM62
# Gap_penalty: 10.0
# Extend_penalty: 0.5
#
# Length: 17
# Identity:      14/17 (82.4%)
# Similarity:    14/17 (82.4%)
# Gaps:           3/17 (17.6%)
# Score: 80.0
#
#
#=======================================

seqA2              1 YQEPVLGPVRGPFP---     14
                     ||||||||||||||
seqB2              1 YQEPVLGPVRGPFPIIV     17


#---------------------------------------
#---------------------------------------
"""


def test_parse_needleall_pairs_extracts_both_blocks_correctly(tmp_path):
    output_path = tmp_path / "out.pair"
    output_path.write_text(_SAMPLE_OUTPUT, encoding="utf-8")
    pairs = parse_needleall_pairs(output_path)

    assert len(pairs) == 2
    first, second = pairs

    assert first["seq1_id"] == "seqA1"
    assert first["seq2_id"] == "seqB1"
    assert first["alignment_length"] == 3
    assert first["identity_count"] == 2
    assert first["identity_pct"] == 66.7
    assert first["gaps_pct"] == 0.0
    assert first["score"] == 15.0

    assert second["seq1_id"] == "seqA2"
    assert second["seq2_id"] == "seqB2"
    assert second["identity_count"] == 14
    assert second["identity_denominator"] == 17
    assert second["identity_pct"] == 82.4
    assert second["gaps_pct"] == 17.6


def test_parse_needleall_pairs_returns_empty_list_for_no_alignments(tmp_path):
    output_path = tmp_path / "empty.pair"
    output_path.write_text("########################################\n# no pairs\n", encoding="utf-8")
    assert parse_needleall_pairs(output_path) == []


def test_run_needleall_defaults_to_a_very_low_minscore():
    # Regression test for a real bug: needleall's own default -minscore
    # (1.0) silently drops low/negative-score pairs from the output
    # entirely (confirmed empirically: a 38x1205 real run returned only
    # 35,076 of the expected 45,790 pairs at the default). A completeness-
    # audited homology scan must never silently lose pairs this way.
    import inspect

    default_minscore = inspect.signature(run_needleall).parameters["minscore"].default
    assert default_minscore <= -100
