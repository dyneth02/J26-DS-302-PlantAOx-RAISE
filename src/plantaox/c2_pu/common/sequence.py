"""Peptide sequence validation, fragmentation, and residue-alphabet checks."""

from __future__ import annotations

import hashlib
import re

STANDARD_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
_VALID_SEQUENCE_RE = re.compile(f"^[{STANDARD_AMINO_ACIDS}]+$")


def normalize_sequence(raw: str) -> str:
    """Upper-case and strip whitespace. Does not validate the alphabet."""
    return str(raw).strip().upper()


def is_standard_alphabet(sequence: str) -> bool:
    """True if every residue is one of the 20 standard amino acids."""
    return bool(_VALID_SEQUENCE_RE.match(sequence))


def is_valid_peptide(sequence: str, min_len: int = 3, max_len: int = 50) -> bool:
    """Standard-alphabet check plus the project's shared 3-50 AA length window."""
    return min_len <= len(sequence) <= max_len and is_standard_alphabet(sequence)


def make_peptide_id(sequence: str, prefix: str = "AOP") -> str:
    """Deterministic, content-addressed peptide ID (stable across re-runs)."""
    digest = hashlib.sha1(sequence.encode("ascii")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"
