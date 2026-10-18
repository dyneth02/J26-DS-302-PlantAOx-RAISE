"""Predictor-independent sequence-to-score contract for Task 3.19."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
import json
import math
from numbers import Real
from pathlib import Path
from typing import Protocol, final, runtime_checkable

from .config import STANDARD_AMINO_ACIDS


PREDICTOR_INTERFACE_VERSION = "1.0"
DEFAULT_INTERFACE_PATH = Path(__file__).with_name("predictor_interface_v1.json")


class PredictorError(RuntimeError):
    """Base exception for failures at the common predictor boundary."""


class InvalidPredictorInputError(PredictorError):
    """Raised before prediction when a sequence violates the input contract."""


class PredictorUnavailableError(PredictorError):
    """Raised when an adapter's model, service, or dependency is unavailable."""


class PredictorScoringError(PredictorError):
    """Raised when an available predictor fails while producing a score."""


class InvalidPredictorScoreError(PredictorError):
    """Raised when a predictor returns a non-numeric or non-finite score."""


@dataclass(frozen=True, slots=True)
class PredictorDescriptor:
    """Stable identity and version metadata for a predictor adapter."""

    predictor_id: str
    display_name: str
    version: str

    def __post_init__(self) -> None:
        for field_name in ("predictor_id", "display_name", "version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{field_name} must be a non-empty trimmed string")


@runtime_checkable
class Predictor(Protocol):
    """Structural interface consumed by downstream C3 scoring code."""

    @property
    def descriptor(self) -> PredictorDescriptor:
        """Return stable predictor identity and version metadata."""

    def score(self, sequence: str) -> float:
        """Return one finite numeric score for one validated peptide sequence."""


def validate_predictor_sequence(sequence: object) -> str:
    """Validate the shared uppercase standard-amino-acid input contract."""

    if not isinstance(sequence, str):
        raise InvalidPredictorInputError("sequence must be a string")
    if not sequence:
        raise InvalidPredictorInputError("sequence must not be empty")
    if sequence != sequence.upper():
        raise InvalidPredictorInputError("sequence must use uppercase amino-acid symbols")
    invalid = sorted(set(sequence) - STANDARD_AMINO_ACIDS)
    if invalid:
        raise InvalidPredictorInputError(
            f"sequence contains non-standard amino-acid symbols: {invalid}"
        )
    return sequence


def normalize_predictor_score(raw_score: object, predictor_id: str) -> float:
    """Convert a real-valued score to a finite built-in float."""

    if isinstance(raw_score, bool) or not isinstance(raw_score, Real):
        raise InvalidPredictorScoreError(
            f"Predictor {predictor_id!r} returned a non-numeric score"
        )
    score = float(raw_score)
    if not math.isfinite(score):
        raise InvalidPredictorScoreError(
            f"Predictor {predictor_id!r} returned a non-finite score"
        )
    return score


class BasePredictorAdapter(ABC):
    """Architecture-neutral base that enforces the common boundary contract."""

    def __init__(self, descriptor: PredictorDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> PredictorDescriptor:
        return self._descriptor

    def ensure_available(self) -> None:
        """Raise PredictorUnavailableError when required resources are unavailable."""

    @abstractmethod
    def _score_validated(self, sequence: str) -> object:
        """Invoke predictor-specific scoring for an already validated sequence."""

    @final
    def score(self, sequence: str) -> float:
        """Validate input, invoke the adapter, and normalize its score or failure."""

        validated = validate_predictor_sequence(sequence)
        try:
            self.ensure_available()
        except PredictorUnavailableError:
            raise
        except Exception as exc:
            raise PredictorUnavailableError(
                f"Predictor {self.descriptor.predictor_id!r} availability check failed"
            ) from exc

        try:
            raw_score = self._score_validated(validated)
        except PredictorError:
            raise
        except Exception as exc:
            raise PredictorScoringError(
                f"Predictor {self.descriptor.predictor_id!r} failed to score "
                f"a sequence of length {len(validated)}"
            ) from exc
        return normalize_predictor_score(raw_score, self.descriptor.predictor_id)


class CallablePredictorAdapter(BasePredictorAdapter):
    """Wrap any one-sequence callable behind the common predictor interface."""

    def __init__(
        self,
        descriptor: PredictorDescriptor,
        scorer: Callable[[str], object],
        availability_check: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(descriptor)
        if not callable(scorer):
            raise TypeError("scorer must be callable")
        if availability_check is not None and not callable(availability_check):
            raise TypeError("availability_check must be callable when provided")
        self._scorer = scorer
        self._availability_check = availability_check

    def ensure_available(self) -> None:
        if self._availability_check is None:
            return
        try:
            available = self._availability_check()
        except Exception as exc:
            raise PredictorUnavailableError(
                f"Predictor {self.descriptor.predictor_id!r} availability check failed"
            ) from exc
        if available is not True:
            raise PredictorUnavailableError(
                f"Predictor {self.descriptor.predictor_id!r} is unavailable"
            )

    def _score_validated(self, sequence: str) -> object:
        return self._scorer(sequence)


def interface_definition() -> dict[str, object]:
    """Return the canonical machine-readable predictor interface contract."""

    return {
        "interface_name": "c3_aop_bcs_predictor",
        "interface_version": PREDICTOR_INTERFACE_VERSION,
        "operation": {
            "signature": "score(sequence: str) -> float",
            "cardinality": "one peptide sequence produces one predictor score",
        },
        "input_contract": {
            "type": "string",
            "non_empty": True,
            "case": "uppercase",
            "alphabet": "".join(sorted(STANDARD_AMINO_ACIDS)),
        },
        "output_contract": {
            "type": "finite Python float",
            "range": "predictor-native; normalization is a later pipeline concern",
            "boolean_allowed": False,
            "nan_or_infinity_allowed": False,
        },
        "required_metadata": ["predictor_id", "display_name", "version"],
        "architecture_boundary": (
            "downstream C3 code depends only on Predictor.descriptor and "
            "Predictor.score, never predictor-specific model internals"
        ),
        "errors": {
            "InvalidPredictorInputError": "input violates the sequence contract",
            "PredictorUnavailableError": "model, service, or dependency is unavailable",
            "PredictorScoringError": "an available predictor failed during scoring",
            "InvalidPredictorScoreError": "result is non-numeric or non-finite",
        },
    }


def write_interface_document(path: str | Path = DEFAULT_INTERFACE_PATH) -> Path:
    """Write the canonical interface contract with deterministic formatting."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(interface_definition(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def main() -> None:
    output_path = write_interface_document()
    print(
        f"Wrote predictor interface {PREDICTOR_INTERFACE_VERSION} to {output_path}"
    )


if __name__ == "__main__":
    main()
