"""Cached, resumable predictor scoring pipeline for Task 3.23."""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .dummy_predictor import (
    DUMMY_SCORING_METHOD,
    DummySmokeTestPredictor,
)
from .perturbation_pipeline import COMBINED_DATASET_VERSION
from .perturbation_schema import PERTURBATION_FIELDS, PerturbationRecord
from .predictor_interface import Predictor
from .standardization import REPOSITORY_ROOT


SCORING_SCHEMA_VERSION = "1.0"
SCORING_PIPELINE_VERSION = "c3_aop_bcs_predictor_scoring_v1"
SCORING_DATASET_VERSION = "c3_aop_bcs_dummy_scored_perturbations_v1"

DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "combined_perturbations_v1.csv"
)
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "dummy_scored_perturbations_v1.csv"
)
DEFAULT_CACHE_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "dummy_sequence_score_cache_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "dummy_predictor_scoring_report_v1.json"
)

CACHE_FIELDS = (
    "score_schema_version",
    "predictor_id",
    "predictor_display_name",
    "predictor_version",
    "scoring_method",
    "software_testing_only",
    "sequence_sha256",
    "sequence",
    "score",
)
SCORED_PERTURBATION_FIELDS = (
    "score_schema_version",
    "predictor_id",
    "predictor_display_name",
    "predictor_version",
    "scoring_method",
    "software_testing_only",
    *PERTURBATION_FIELDS,
    "original_score",
    "perturbed_score",
)


class PredictorScoreCacheError(ValueError):
    """Raised when a persisted score cache is invalid or has wrong provenance."""


@dataclass(frozen=True, slots=True)
class ScoringRunResult:
    """Summary of one completed cached scoring run."""

    report: dict[str, Any]
    initial_cache_entries: int
    scores_computed: int
    cache_hits: int


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def _score_text(score: float) -> str:
    return format(score, ".17g")


def _testing_only(predictor: Predictor) -> bool:
    return getattr(predictor, "software_testing_only", False) is True


def _metadata(predictor: Predictor, scoring_method: str) -> dict[str, str]:
    if not isinstance(scoring_method, str) or not scoring_method.strip():
        raise ValueError("scoring_method must be a non-empty string")
    if scoring_method != scoring_method.strip():
        raise ValueError("scoring_method must be trimmed")
    descriptor = predictor.descriptor
    return {
        "score_schema_version": SCORING_SCHEMA_VERSION,
        "predictor_id": descriptor.predictor_id,
        "predictor_display_name": descriptor.display_name,
        "predictor_version": descriptor.version,
        "scoring_method": scoring_method,
        "software_testing_only": str(_testing_only(predictor)).lower(),
    }


def _read_perturbations(path: Path) -> list[PerturbationRecord]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != PERTURBATION_FIELDS:
            raise ValueError("Input schema does not match the perturbation contract")
        records = [PerturbationRecord.from_mapping(row) for row in reader]
    if len({record.variant_id for record in records}) != len(records):
        raise ValueError("Input contains duplicate variant identifiers")
    return records


def _load_cache(
    path: Path,
    expected_metadata: Mapping[str, str],
) -> dict[str, float]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != CACHE_FIELDS:
            raise PredictorScoreCacheError("Score cache schema is invalid")
        cached: dict[str, float] = {}
        for row_number, row in enumerate(reader, start=2):
            for field, expected in expected_metadata.items():
                if row[field] != expected:
                    raise PredictorScoreCacheError(
                        f"Score cache {field} does not match the active predictor "
                        f"at row {row_number}"
                    )
            sequence = row["sequence"]
            if row["sequence_sha256"] != _sequence_sha256(sequence):
                raise PredictorScoreCacheError(
                    f"Score cache sequence hash is invalid at row {row_number}"
                )
            try:
                score = float(row["score"])
            except ValueError as exc:
                raise PredictorScoreCacheError(
                    f"Score cache value is not numeric at row {row_number}"
                ) from exc
            if not math.isfinite(score):
                raise PredictorScoreCacheError(
                    f"Score cache value is not finite at row {row_number}"
                )
            if sequence in cached and cached[sequence] != score:
                raise PredictorScoreCacheError(
                    f"Score cache has conflicting entries for sequence {sequence!r}"
                )
            cached[sequence] = score
    return cached


def _write_cache(
    path: Path,
    scores: Mapping[str, float],
    metadata: Mapping[str, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CACHE_FIELDS, lineterminator="\n")
        writer.writeheader()
        for sequence in sorted(scores):
            writer.writerow(
                {
                    **metadata,
                    "sequence_sha256": _sequence_sha256(sequence),
                    "sequence": sequence,
                    "score": _score_text(scores[sequence]),
                }
            )
    temporary_path.replace(path)


def _ordered_unique_sequences(
    records: Sequence[PerturbationRecord],
) -> tuple[list[str], set[str], set[str]]:
    originals = {record.original_sequence for record in records}
    perturbed = {record.perturbed_sequence for record in records}
    ordered = list(dict.fromkeys(
        [record.original_sequence for record in records]
        + [record.perturbed_sequence for record in records]
    ))
    return ordered, originals, perturbed


def score_sequences_with_cache(
    sequences: Iterable[str],
    predictor: Predictor,
    scoring_method: str,
    cache_path: str | Path,
    checkpoint_interval: int = 100,
) -> tuple[dict[str, float], int, int, int]:
    """Score missing unique sequences and checkpoint a provenance-bound cache."""

    if (
        isinstance(checkpoint_interval, bool)
        or not isinstance(checkpoint_interval, int)
        or checkpoint_interval < 1
    ):
        raise ValueError("checkpoint_interval must be a positive integer")
    metadata = _metadata(predictor, scoring_method)
    path = Path(cache_path)
    cached = _load_cache(path, metadata)
    initial_entries = len(cached)
    requested = list(dict.fromkeys(sequences))
    cache_hits = sum(sequence in cached for sequence in requested)
    computed = 0
    since_checkpoint = 0
    try:
        for sequence in requested:
            if sequence in cached:
                continue
            cached[sequence] = predictor.score(sequence)
            computed += 1
            since_checkpoint += 1
            if since_checkpoint >= checkpoint_interval:
                _write_cache(path, cached, metadata)
                since_checkpoint = 0
    except BaseException:
        if computed:
            _write_cache(path, cached, metadata)
        raise
    if computed or not path.exists():
        _write_cache(path, cached, metadata)
    return ({sequence: cached[sequence] for sequence in requested}, initial_entries, computed, cache_hits)


def _write_scored_records(
    path: Path,
    records: Sequence[PerturbationRecord],
    scores: Mapping[str, float],
    metadata: Mapping[str, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=SCORED_PERTURBATION_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    **metadata,
                    **record.as_dict(),
                    "original_score": _score_text(scores[record.original_sequence]),
                    "perturbed_score": _score_text(scores[record.perturbed_sequence]),
                }
            )


def build_scored_perturbation_dataset(
    predictor: Predictor,
    scoring_method: str,
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    checkpoint_interval: int = 100,
    created_on: date | None = None,
    dataset_version: str = SCORING_DATASET_VERSION,
) -> ScoringRunResult:
    """Score all unique originals/variants and export one row per perturbation."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    cache_path = Path(cache_path)
    report_path = Path(report_path)
    records = _read_perturbations(input_path)
    ordered_sequences, originals, perturbed = _ordered_unique_sequences(records)
    scores, initial_entries, computed, cache_hits = score_sequences_with_cache(
        ordered_sequences,
        predictor,
        scoring_method,
        cache_path,
        checkpoint_interval,
    )
    metadata = _metadata(predictor, scoring_method)
    _write_scored_records(output_path, records, scores, metadata)

    type_counts = Counter(record.perturbation_type for record in records)
    report = {
        "schema_version": SCORING_SCHEMA_VERSION,
        "pipeline_version": SCORING_PIPELINE_VERSION,
        "dataset_version": dataset_version,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": COMBINED_DATASET_VERSION,
        "source": {
            "path": _display_path(input_path),
            "sha256": _sha256(input_path),
        },
        "predictor": {
            "predictor_id": predictor.descriptor.predictor_id,
            "display_name": predictor.descriptor.display_name,
            "version": predictor.descriptor.version,
            "scoring_method": scoring_method,
            "software_testing_only": _testing_only(predictor),
        },
        "counts": {
            "original_peptide_count": len({record.sequence_id for record in records}),
            "unique_original_sequence_count": len(originals),
            "perturbation_count": len(records),
            "perturbations_by_type": {
                perturbation_type: type_counts[perturbation_type]
                for perturbation_type in ("P1", "P2", "P3")
            },
            "unique_perturbed_sequence_count": len(perturbed),
            "unique_sequence_count": len(ordered_sequences),
        },
        "cache": {
            "path": _display_path(cache_path),
            "checkpoint_interval": checkpoint_interval,
            "initial_entries": initial_entries,
            "requested_unique_sequences": len(ordered_sequences),
            "cache_hits": cache_hits,
            "scores_computed": computed,
            "final_entries": initial_entries + computed,
            "resume_supported": True,
            "provenance_validation": (
                "schema, predictor identity, predictor version, scoring method, "
                "testing classification, sequence hash, and finite score"
            ),
            "sha256": _sha256(cache_path),
        },
        "output": {
            "path": _display_path(output_path),
            "record_count": len(records),
            "fields": list(SCORED_PERTURBATION_FIELDS),
            "sha256": _sha256(output_path),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return ScoringRunResult(report, initial_entries, computed, cache_hits)


def main() -> None:
    predictor = DummySmokeTestPredictor()
    result = build_scored_perturbation_dataset(
        predictor=predictor,
        scoring_method=DUMMY_SCORING_METHOD,
    )
    counts = result.report["counts"]
    print(
        f'Scored {counts["original_peptide_count"]} originals and '
        f'{counts["perturbation_count"]} P1/P2/P3 variants with the '
        "non-experimental dummy predictor."
    )


if __name__ == "__main__":
    main()
