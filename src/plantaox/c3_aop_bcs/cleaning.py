"""Validate, filter, and exactly deduplicate standardized C3 peptide records."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import ResearchConfig, STANDARD_AMINO_ACIDS, load_research_config
from .standardization import OUTPUT_FIELDS as STANDARDIZED_FIELDS
from .standardization import REPOSITORY_ROOT, STANDARDIZED_DATASET_VERSION


DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT / "data" / "interim" / "c3_aop_bcs" / "standardized_aop_candidates_v1.csv"
)
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "cleaned_aop_sequences_v1.csv"
)
DEFAULT_EXCLUSIONS_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "sequence_cleaning_exclusions_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "sequence_cleaning_report_v1.json"
)
CLEANED_DATASET_VERSION = "c3_aop_bcs_cleaned_v1"

OUTPUT_FIELDS = (*STANDARDIZED_FIELDS, "sequence_length")
EXCLUSION_FIELDS = (
    *STANDARDIZED_FIELDS,
    "sequence_length",
    "exclusion_reason",
    "invalid_residues",
    "retained_sequence_id",
)
REJECTION_REASONS = (
    "missing_sequence",
    "invalid_amino_acid",
    "length_out_of_range",
    "exact_duplicate",
)


def validate_sequence(
    sequence: str | None,
    minimum_length: int,
    maximum_length: int,
) -> tuple[str | None, tuple[str, ...]]:
    """Return the first exclusive rejection reason and any invalid symbols."""

    if not sequence:
        return "missing_sequence", ()

    invalid_residues = tuple(sorted(set(sequence) - STANDARD_AMINO_ACIDS))
    if invalid_residues:
        return "invalid_amino_acid", invalid_residues

    if not minimum_length <= len(sequence) <= maximum_length:
        return "length_out_of_range", ()

    return None, ()


def _evidence_priority(record: Mapping[str, Any]) -> int:
    return 0 if record.get("evidence_tier_candidate") == "E1" else 1


def clean_records(
    records: Iterable[Mapping[str, Any]],
    config: ResearchConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Apply exclusive validation rules and deterministic exact deduplication.

    Valid duplicate groups retain an E1 record when one exists; ties retain the
    earliest standardized input record. This keeps the strongest available
    evidence while making generation reproducible.
    """

    materialized = [dict(record) for record in records]
    eligible_by_sequence: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    exclusions: list[tuple[int, dict[str, Any]]] = []
    reason_counts: Counter[str] = Counter()

    for position, record in enumerate(materialized):
        sequence = str(record.get("peptide_sequence") or "")
        reason, invalid_residues = validate_sequence(
            sequence,
            config.sequence_min_length,
            config.sequence_max_length,
        )
        if reason is None:
            eligible_by_sequence[sequence].append((position, record))
            continue

        reason_counts[reason] += 1
        exclusions.append(
            (
                position,
                {
                    **record,
                    "sequence_length": len(sequence),
                    "exclusion_reason": reason,
                    "invalid_residues": "".join(invalid_residues),
                    "retained_sequence_id": "",
                },
            )
        )

    retained_with_positions: list[tuple[int, dict[str, Any]]] = []
    for sequence, candidates in eligible_by_sequence.items():
        retained_position, retained_record = min(
            candidates,
            key=lambda item: (_evidence_priority(item[1]), item[0]),
        )
        retained_with_positions.append(
            (retained_position, {**retained_record, "sequence_length": len(sequence)})
        )
        retained_id = str(retained_record.get("sequence_id") or "")
        for position, duplicate in candidates:
            if position == retained_position:
                continue
            reason_counts["exact_duplicate"] += 1
            exclusions.append(
                (
                    position,
                    {
                        **duplicate,
                        "sequence_length": len(sequence),
                        "exclusion_reason": "exact_duplicate",
                        "invalid_residues": "",
                        "retained_sequence_id": retained_id,
                    },
                )
            )

    retained = [record for _, record in sorted(retained_with_positions)]
    ordered_exclusions = [record for _, record in sorted(exclusions)]
    counts = {
        "original_count": len(materialized),
        "missing_count": reason_counts["missing_sequence"],
        "invalid_count": reason_counts["invalid_amino_acid"],
        "out_of_range_count": reason_counts["length_out_of_range"],
        "exact_duplicate_count": reason_counts["exact_duplicate"],
        "retained_count": len(retained),
    }
    if sum(counts[key] for key in counts if key != "original_count") != counts["original_count"]:
        raise RuntimeError("Sequence cleaning counts do not reconcile with the input count")
    return retained, ordered_exclusions, counts


def _read_standardized_records(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != STANDARDIZED_FIELDS:
            raise ValueError("Standardized input schema does not match the Task 3.5 contract")
        return list(reader)


def _write_csv(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
    fieldnames: tuple[str, ...],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def _display_path(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix() if path.is_relative_to(REPOSITORY_ROOT) else str(path)


def _artifact(path: Path, record_count: int) -> dict[str, str | int]:
    return {
        "path": _display_path(path),
        "record_count": record_count,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_cleaned_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    exclusions_path: str | Path = DEFAULT_EXCLUSIONS_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Create the validated dataset, exclusion ledger, and cleaning report."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    exclusions_path = Path(exclusions_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()
    records = _read_standardized_records(input_path)
    retained, exclusions, counts = clean_records(records, active_config)

    _write_csv(retained, output_path, OUTPUT_FIELDS)
    _write_csv(exclusions, exclusions_path, EXCLUSION_FIELDS)

    report = {
        "schema_version": "1.0",
        "dataset_version": CLEANED_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": STANDARDIZED_DATASET_VERSION,
        "source": {
            "path": _display_path(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "validation": {
            "standard_amino_acids": "".join(sorted(STANDARD_AMINO_ACIDS)),
            "minimum_length": active_config.sequence_min_length,
            "maximum_length": active_config.sequence_max_length,
            "rejection_order": list(REJECTION_REASONS),
            "counts_are_mutually_exclusive": True,
        },
        "exact_duplicate_policy": (
            "group by exact standardized peptide_sequence; retain E1 over E2, "
            "then the earliest standardized input record"
        ),
        "counts": counts,
        "outputs": {
            "cleaned": _artifact(output_path, len(retained)),
            "exclusions": _artifact(exclusions_path, len(exclusions)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_cleaned_dataset()
    counts = report["counts"]
    print(
        f'Cleaned {counts["original_count"]} records: retained {counts["retained_count"]}, '
        f'excluded {counts["original_count"] - counts["retained_count"]}'
    )


if __name__ == "__main__":
    main()
