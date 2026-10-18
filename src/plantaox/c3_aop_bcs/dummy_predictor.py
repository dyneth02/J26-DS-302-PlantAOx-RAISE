"""Deterministic non-experimental predictor for Task 3.22 software tests."""

from __future__ import annotations

import json
from pathlib import Path

from .config import STANDARD_AMINO_ACIDS
from .predictor_interface import BasePredictorAdapter, PredictorDescriptor


DUMMY_PREDICTOR_VERSION = "1.0.0"
DUMMY_PREDICTOR_ID = "c3_software_smoke_test_dummy"
DUMMY_SCORING_METHOD = "position_weighted_alphabetical_residue_rank_checksum"
DEFAULT_DUMMY_DEFINITION_PATH = Path(__file__).with_name("dummy_predictor_v1.json")

SOFTWARE_TESTING_ONLY = True
SCIENTIFIC_AOP_PREDICTOR = False
EXPERIMENTAL_RESULTS_ALLOWED = False

_ORDERED_AMINO_ACIDS = tuple(sorted(STANDARD_AMINO_ACIDS))
_RESIDUE_RANK = {
    residue: rank for rank, residue in enumerate(_ORDERED_AMINO_ACIDS, start=1)
}


class DummySmokeTestPredictor(BasePredictorAdapter):
    """Arbitrary deterministic scorer that must never be used as scientific evidence."""

    software_testing_only = SOFTWARE_TESTING_ONLY
    scientific_aop_predictor = SCIENTIFIC_AOP_PREDICTOR
    experimental_results_allowed = EXPERIMENTAL_RESULTS_ALLOWED

    def __init__(self) -> None:
        super().__init__(
            PredictorDescriptor(
                predictor_id=DUMMY_PREDICTOR_ID,
                display_name="C3 software smoke-test dummy (NON-EXPERIMENTAL)",
                version=DUMMY_PREDICTOR_VERSION,
            )
        )

    def _score_validated(self, sequence: str) -> float:
        """Return an arbitrary position-weighted residue-rank checksum in [0, 1]."""

        weighted_sum = sum(
            position * _RESIDUE_RANK[residue]
            for position, residue in enumerate(sequence, start=1)
        )
        position_sum = len(sequence) * (len(sequence) + 1) // 2
        return weighted_sum / (len(_ORDERED_AMINO_ACIDS) * position_sum)


def dummy_predictor_definition() -> dict[str, object]:
    """Return the canonical safety and implementation metadata for the dummy."""

    return {
        "predictor_id": DUMMY_PREDICTOR_ID,
        "display_name": "C3 software smoke-test dummy (NON-EXPERIMENTAL)",
        "version": DUMMY_PREDICTOR_VERSION,
        "interface_version": "1.0",
        "classification": {
            "software_testing_only": SOFTWARE_TESTING_ONLY,
            "scientific_aop_predictor": SCIENTIFIC_AOP_PREDICTOR,
            "experimental_results_allowed": EXPERIMENTAL_RESULTS_ALLOWED,
        },
        "warning": (
            "This deterministic dummy is only for software pipeline tests. It is not "
            "a scientific antioxidant-peptide predictor and its scores must never be "
            "reported as experimental results or biological evidence."
        ),
        "scoring_method": {
            "name": DUMMY_SCORING_METHOD,
            "formula": (
                "sum(position * alphabetical_residue_rank) / "
                "(20 * sum(positions))"
            ),
            "amino_acid_order": "".join(_ORDERED_AMINO_ACIDS),
            "position_indexing": "one-based",
            "output_range": [0.0, 1.0],
            "biological_basis": "none",
        },
        "allowed_uses": [
            "predictor-interface smoke tests",
            "scoring-pipeline smoke tests",
            "metric-pipeline smoke tests",
            "failure-handling and reproducibility tests",
        ],
        "prohibited_uses": [
            "scientific AOP prediction",
            "experimental results",
            "predictor comparison",
            "biological interpretation",
            "satisfying the PP1 real-predictor requirement",
        ],
    }


def write_dummy_predictor_definition(
    path: str | Path = DEFAULT_DUMMY_DEFINITION_PATH,
) -> Path:
    """Write the canonical dummy definition with deterministic formatting."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dummy_predictor_definition(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def main() -> None:
    output_path = write_dummy_predictor_definition()
    print(f"Wrote non-experimental dummy definition to {output_path}")


if __name__ == "__main__":
    main()
