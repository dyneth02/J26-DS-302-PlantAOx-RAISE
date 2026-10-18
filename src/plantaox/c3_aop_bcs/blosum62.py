"""Load BLOSUM62 and select deterministic P2 substitution candidates."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from .config import STANDARD_AMINO_ACIDS, load_research_config


DEFAULT_MATRIX_PATH = Path(__file__).with_name("resources") / "blosum62_standard.tsv"
DEFAULT_MANIFEST_PATH = Path(__file__).with_name("blosum62_support_v1.json")
BLOSUM62_SOURCE_URL = "https://ftp.ncbi.nlm.nih.gov/blast/matrices/BLOSUM62"
BLOSUM62_SUPPORT_VERSION = "c3_aop_bcs_blosum62_support_v1"
MATRIX_ALPHABET = tuple("ARNDCQEGHILKMFPSTWYV")
MINIMUM_CONSERVATIVE_SCORE = 1
TIE_BREAK_RULE = "highest BLOSUM62 score, then alphabetical residue code ascending"

Blosum62Matrix = dict[tuple[str, str], int]


@dataclass(frozen=True, slots=True)
class SubstitutionCandidate:
    """One eligible substitution and its BLOSUM62 score."""

    residue: str
    score: int


def load_blosum62(path: str | Path = DEFAULT_MATRIX_PATH) -> Blosum62Matrix:
    """Load and validate the project-pinned 20-amino-acid BLOSUM62 table."""

    matrix_path = Path(path)
    data_lines = [
        line
        for line in matrix_path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    reader = csv.reader(data_lines, delimiter="\t")
    rows = list(reader)
    if not rows or tuple(rows[0][1:]) != MATRIX_ALPHABET:
        raise ValueError("BLOSUM62 column alphabet does not match the pinned matrix contract")
    if len(rows) != len(MATRIX_ALPHABET) + 1:
        raise ValueError("BLOSUM62 must contain exactly 20 standard-amino-acid rows")

    matrix: Blosum62Matrix = {}
    observed_rows: list[str] = []
    for row in rows[1:]:
        if len(row) != len(MATRIX_ALPHABET) + 1:
            raise ValueError("BLOSUM62 row has an invalid number of columns")
        row_residue = row[0]
        observed_rows.append(row_residue)
        for column_residue, raw_score in zip(MATRIX_ALPHABET, row[1:]):
            try:
                matrix[(row_residue, column_residue)] = int(raw_score)
            except ValueError as exc:
                raise ValueError("BLOSUM62 contains a non-integer score") from exc

    if tuple(observed_rows) != MATRIX_ALPHABET:
        raise ValueError("BLOSUM62 row alphabet does not match the column alphabet")
    if set(MATRIX_ALPHABET) != STANDARD_AMINO_ACIDS:
        raise RuntimeError("Pinned BLOSUM62 alphabet does not match the project amino-acid set")
    for left in MATRIX_ALPHABET:
        for right in MATRIX_ALPHABET:
            if matrix[(left, right)] != matrix[(right, left)]:
                raise ValueError(f"BLOSUM62 matrix is not symmetric at {left}/{right}")
    return matrix


def evaluate_substitution_candidates(
    original_residue: str,
    matrix: Mapping[tuple[str, str], int],
    redox_residues: Sequence[str],
    minimum_score: int = MINIMUM_CONSERVATIVE_SCORE,
) -> tuple[SubstitutionCandidate, ...]:
    """Return eligible candidates ordered by score then deterministic tie-break."""

    if original_residue not in STANDARD_AMINO_ACIDS:
        raise ValueError("original_residue must be a standard amino acid")
    if isinstance(minimum_score, bool) or not isinstance(minimum_score, int):
        raise ValueError("minimum_score must be an integer")
    excluded = {original_residue, "A", *redox_residues}
    candidates = [
        SubstitutionCandidate(candidate, matrix[(original_residue, candidate)])
        for candidate in sorted(STANDARD_AMINO_ACIDS - excluded)
        if matrix[(original_residue, candidate)] >= minimum_score
    ]
    return tuple(sorted(candidates, key=lambda candidate: (-candidate.score, candidate.residue)))


def select_conservative_substitution(
    original_residue: str,
    matrix: Mapping[tuple[str, str], int],
    redox_residues: Sequence[str],
    minimum_score: int = MINIMUM_CONSERVATIVE_SCORE,
) -> SubstitutionCandidate | None:
    """Select the highest-scoring eligible candidate, or None when none exists."""

    candidates = evaluate_substitution_candidates(
        original_residue,
        matrix,
        redox_residues,
        minimum_score,
    )
    return candidates[0] if candidates else None


def support_manifest(matrix_path: str | Path = DEFAULT_MATRIX_PATH) -> dict[str, object]:
    """Return provenance and frozen selection rules for Task 3.12."""

    path = Path(matrix_path)
    matrix = load_blosum62(path)
    config = load_research_config()
    selectable_originals = sorted(STANDARD_AMINO_ACIDS - set(config.redox_residues))
    selections = {
        residue: (
            None
            if (choice := select_conservative_substitution(
                residue,
                matrix,
                config.redox_residues,
            )) is None
            else {"residue": choice.residue, "score": choice.score}
        )
        for residue in selectable_originals
    }
    return {
        "support_version": BLOSUM62_SUPPORT_VERSION,
        "matrix_name": "BLOSUM62",
        "score_units": "half-bit log-odds scores",
        "source_url": BLOSUM62_SOURCE_URL,
        "local_resource": str(path.relative_to(Path(__file__).parent).as_posix()),
        "resource_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "alphabet": list(MATRIX_ALPHABET),
        "dimensions": [len(MATRIX_ALPHABET), len(MATRIX_ALPHABET)],
        "selection_rule": {
            "minimum_score": MINIMUM_CONSERVATIVE_SCORE,
            "excluded_candidates": ["original_residue", "A", *config.redox_residues],
            "tie_break": TIE_BREAK_RULE,
        },
        "selected_substitutions_for_non_redox_originals": selections,
    }


def write_support_manifest(path: str | Path = DEFAULT_MANIFEST_PATH) -> Path:
    """Write deterministic BLOSUM62 provenance and rule metadata."""

    output_path = Path(path)
    output_path.write_text(
        json.dumps(support_manifest(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def main() -> None:
    matrix = load_blosum62()
    output_path = write_support_manifest()
    print(f"Loaded {len(matrix)} BLOSUM62 scores and wrote {output_path}")


if __name__ == "__main__":
    main()
