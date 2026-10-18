"""Candidate length, alphabet, and amino-acid composition filters."""

from __future__ import annotations

from collections import Counter

STANDARD_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")


def filter_fragments(fragments: list[dict], min_length: int = 3, max_length: int = 20,
                     min_unique_amino_acids: int = 2) -> tuple[list[dict], dict[str, int]]:
    """Apply length then composition/alphabet filters and return funnel counts."""
    length_pass = [r for r in fragments if min_length <= len(r["sequence"]) <= max_length]
    composition_pass = [r for r in length_pass
                        if set(r["sequence"]) <= STANDARD_AA
                        and len(set(r["sequence"])) >= min_unique_amino_acids]
    return composition_pass, {"raw_fragments": len(fragments), "length_filtered": len(length_pass),
                              "composition_filtered": len(composition_pass)}


def summarize_exclusions(exclusions: list[dict]) -> dict[str, int]:
    return dict(sorted(Counter(r["exclusion_reason"] for r in exclusions).items()))
