"""Load Biopython's BLOSUM62 and select deterministic P2 candidates."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence

import Bio
from Bio.Align import substitution_matrices

from .config import STANDARD_AMINO_ACIDS, load_research_config


DEFAULT_MANIFEST_PATH = Path(__file__).with_name("blosum62_support_v1.json")
BLOSUM62_SOURCE_URL = "https://ftp.ncbi.nlm.nih.gov/blast/matrices/BLOSUM62"
BLOSUM62_SUPPORT_VERSION = "c3_aop_bcs_blosum62_support_v1"
BLOSUM62_MATRIX_NAME = "BLOSUM62"
BLOSUM62_LOADER = "Bio.Align.substitution_matrices.load"
MATRIX_ALPHABET = tuple("ARNDCQEGHILKMFPSTWYV")
MINIMUM_CONSERVATIVE_SCORE = 1
TIE_BREAK_RULE = "highest BLOSUM62 score, then alphabetical residue code ascending"

Blosum62Matrix = dict[tuple[str, str], int]


@dataclass(frozen=True, slots=True)
class SubstitutionCandidate:
    """One eligible substitution and its BLOSUM62 score."""

    residue: str
    score: int


def load_blosum62() -> Blosum62Matrix:
    """Load BLOSUM62 with Biopython and return its standard-amino-acid subset."""

    library_matrix = substitution_matrices.load(BLOSUM62_MATRIX_NAME)
    library_alphabet = set(library_matrix.alphabet)
    missing_residues = STANDARD_AMINO_ACIDS - library_alphabet
    if missing_residues:
        missing = ", ".join(sorted(missing_residues))
        raise ValueError(f"Biopython BLOSUM62 is missing standard residues: {missing}")
    if set(MATRIX_ALPHABET) != STANDARD_AMINO_ACIDS:
        raise RuntimeError("BLOSUM62 alphabet does not match the project amino-acid set")

    matrix: Blosum62Matrix = {}
    for left in MATRIX_ALPHABET:
        for right in MATRIX_ALPHABET:
            raw_score = float(library_matrix[left, right])
            if not raw_score.is_integer():
                raise ValueError(f"BLOSUM62 score is not an integer at {left}/{right}")
            matrix[(left, right)] = int(raw_score)

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


def support_manifest() -> dict[str, object]:
    """Return provenance and frozen selection rules for Task 3.12."""

    library_matrix = substitution_matrices.load(BLOSUM62_MATRIX_NAME)
    matrix = load_blosum62()
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
        "matrix_provider": {
            "library": "Biopython",
            "version": Bio.__version__,
            "loader": BLOSUM62_LOADER,
            "matrix_identifier": BLOSUM62_MATRIX_NAME,
            "library_alphabet": list(library_matrix.alphabet),
        },
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
    print(
        f"Loaded {len(matrix)} BLOSUM62 scores with Biopython {Bio.__version__} "
        f"and wrote {output_path}"
    )


if __name__ == "__main__":
    main()
