"""Run and validate the combined P1/P2/P3 perturbation pipeline for Task 3.15."""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .blosum62 import Blosum62Matrix, load_blosum62, select_conservative_substitution
from .config import DEFAULT_CONFIG_PATH, ResearchConfig, load_research_config
from .p1_alanine_scanning import P1_DATASET_VERSION, generate_p1_records
from .p2_conservative_substitutions import P2_DATASET_VERSION, generate_p2_records
from .p3_random_controls import (
    P3_DATASET_VERSION,
    generate_p3_records,
    random_substitution_metadata,
    select_random_substitution,
)
from .perturbation_schema import (
    DEFAULT_SCHEMA_PATH,
    PERTURBATION_FIELDS,
    PERTURBATION_SCHEMA_VERSION,
    PerturbationRecord,
)
from .residue_annotation import (
    NON_REDOX_CLASS,
    OUTPUT_FIELDS as ANNOTATION_FIELDS,
    REDOX_CLASS,
    RESIDUE_ANNOTATION_DATASET_VERSION,
)
from .standardization import REPOSITORY_ROOT


DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "residue_annotations_v1.csv"
)
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "combined_perturbations_v1.csv"
)
DEFAULT_REJECTION_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "combined_perturbation_rejections_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "combined_perturbation_pipeline_report_v1.json"
)
COMBINED_DATASET_VERSION = "c3_aop_bcs_combined_perturbations_v1"
PIPELINE_VERSION = "c3_aop_bcs_perturbation_pipeline_v1"
REJECTION_FIELDS = (*PERTURBATION_FIELDS, "rejection_reason")


@dataclass(frozen=True, slots=True)
class RejectedPerturbation:
    """A generated record excluded by combined semantic validation."""

    record: PerturbationRecord
    reason: str

    def as_dict(self) -> dict[str, str | int]:
        return {**self.record.as_dict(), "rejection_reason": self.reason}


def _annotation_index(
    annotations: Iterable[Mapping[str, Any]],
    redox_residues: Sequence[str],
) -> dict[tuple[str, int], dict[str, str]]:
    redox_set = frozenset(redox_residues)
    index: dict[tuple[str, int], dict[str, str]] = {}
    for raw_annotation in annotations:
        annotation = {key: str(value) for key, value in raw_annotation.items()}
        sequence_id = annotation.get("sequence_id", "")
        sequence = annotation.get("peptide_sequence", "")
        residue = annotation.get("residue", "")
        residue_class = annotation.get("residue_class", "")
        try:
            position = int(annotation.get("residue_position", "0"))
        except ValueError as exc:
            raise ValueError(f"Invalid residue position for {sequence_id}") from exc
        if not sequence_id or not 1 <= position <= len(sequence):
            raise ValueError("Annotation contains an invalid sequence identifier or position")
        if sequence[position - 1] != residue:
            raise ValueError(f"Annotation residue mismatch for {sequence_id} at {position}")
        expected_class = REDOX_CLASS if residue in redox_set else NON_REDOX_CLASS
        if residue_class != expected_class:
            raise ValueError(f"Annotation class mismatch for {sequence_id} at {position}")
        key = (sequence_id, position)
        if key in index:
            raise ValueError(f"Duplicate annotation for {sequence_id} at {position}")
        index[key] = annotation
    return index


def validate_generated_variant(
    record: PerturbationRecord,
    annotations_by_position: Mapping[tuple[str, int], Mapping[str, str]],
    config: ResearchConfig,
    matrix: Mapping[tuple[str, str], int],
) -> tuple[str, ...]:
    """Return deterministic semantic rejection reasons for one generated variant."""

    reasons: list[str] = []
    annotation = annotations_by_position.get((record.sequence_id, record.position))
    if annotation is None:
        return ("source_annotation_not_found",)
    if record.original_sequence != annotation["peptide_sequence"]:
        reasons.append("original_sequence_mismatch")
    if record.original_residue != annotation["residue"]:
        reasons.append("original_residue_mismatch")

    if record.perturbation_type == "P1":
        if annotation["residue_class"] != REDOX_CLASS:
            reasons.append("p1_position_not_redox")
        if record.original_residue not in config.redox_residues:
            reasons.append("p1_original_residue_not_redox")
        if record.substituted_residue != "A":
            reasons.append("p1_replacement_not_alanine")
    elif record.perturbation_type == "P2":
        if annotation["residue_class"] != NON_REDOX_CLASS:
            reasons.append("p2_position_not_non_redox")
        expected = select_conservative_substitution(
            record.original_residue,
            matrix,
            config.redox_residues,
        )
        if expected is None:
            reasons.append("p2_no_eligible_candidate")
        else:
            if record.substituted_residue != expected.residue:
                reasons.append("p2_replacement_not_selected_candidate")
            if record.blosum62_score != expected.score:
                reasons.append("p2_blosum62_score_mismatch")
    elif record.perturbation_type == "P3":
        expected = select_random_substitution(
            record.sequence_id,
            record.original_sequence,
            record.position,
            record.original_residue,
            config.random_seed,
        )
        if record.random_seed != config.random_seed:
            reasons.append("p3_master_seed_mismatch")
        if record.substituted_residue != expected.residue:
            reasons.append("p3_replacement_not_seed_derived")
        if record.random_metadata != random_substitution_metadata(expected):
            reasons.append("p3_random_metadata_mismatch")
    return tuple(reasons)


def validate_and_partition_records(
    records: Iterable[PerturbationRecord],
    annotations: Iterable[Mapping[str, Any]],
    config: ResearchConfig,
    matrix: Mapping[tuple[str, str], int],
) -> tuple[list[PerturbationRecord], list[RejectedPerturbation]]:
    """Partition generated records into accepted and rejected collections."""

    annotations_by_position = _annotation_index(annotations, config.redox_residues)
    accepted: list[PerturbationRecord] = []
    rejected: list[RejectedPerturbation] = []
    seen_variant_ids: set[str] = set()
    for record in records:
        reasons = list(
            validate_generated_variant(record, annotations_by_position, config, matrix)
        )
        if record.variant_id in seen_variant_ids:
            reasons.append("duplicate_variant_id")
        seen_variant_ids.add(record.variant_id)
        if reasons:
            rejected.append(RejectedPerturbation(record, ";".join(reasons)))
        else:
            accepted.append(record)
    return accepted, rejected


def _read_annotations(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != ANNOTATION_FIELDS:
            raise ValueError("Input schema does not match the Task 3.9 annotation contract")
        return list(reader)


def _write_records(records: Sequence[PerturbationRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=PERTURBATION_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(record.as_dict() for record in records)


def _write_rejections(
    records: Sequence[RejectedPerturbation],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=REJECTION_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(record.as_dict() for record in records)


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _artifact(path: Path, record_count: int) -> dict[str, str | int]:
    return {
        "path": _display_path(path),
        "record_count": record_count,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_combined_perturbation_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    rejection_path: str | Path = DEFAULT_REJECTION_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    matrix: Blosum62Matrix | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Generate, validate, and export all accepted P1/P2/P3 variants."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    rejection_path = Path(rejection_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()
    active_matrix = load_blosum62() if matrix is None else matrix
    annotations = _read_annotations(input_path)

    generated_by_type = {
        "P1": generate_p1_records(annotations, active_config.redox_residues),
        "P2": generate_p2_records(
            annotations,
            active_matrix,
            active_config.redox_residues,
        ),
        "P3": generate_p3_records(
            annotations,
            active_config.redox_residues,
            active_config.random_seed,
        ),
    }
    generated = [
        record
        for perturbation_type in ("P1", "P2", "P3")
        for record in generated_by_type[perturbation_type]
    ]
    accepted, rejected = validate_and_partition_records(
        generated,
        annotations,
        active_config,
        active_matrix,
    )
    _write_records(accepted, output_path)
    _write_rejections(rejected, rejection_path)

    generated_counts = {
        perturbation_type: len(records)
        for perturbation_type, records in generated_by_type.items()
    }
    accepted_counts = Counter(record.perturbation_type for record in accepted)
    rejected_counts = Counter(item.record.perturbation_type for item in rejected)
    counts = {
        "input_peptide_count": len({str(row["sequence_id"]) for row in annotations}),
        "input_annotation_count": len(annotations),
        "generated_variant_count": len(generated),
        "generated_by_perturbation_type": generated_counts,
        "accepted_variant_count": len(accepted),
        "accepted_by_perturbation_type": {
            perturbation_type: accepted_counts[perturbation_type]
            for perturbation_type in ("P1", "P2", "P3")
        },
        "rejected_variant_count": len(rejected),
        "rejected_by_perturbation_type": {
            perturbation_type: rejected_counts[perturbation_type]
            for perturbation_type in ("P1", "P2", "P3")
        },
    }
    if counts["accepted_variant_count"] + counts["rejected_variant_count"] != counts[
        "generated_variant_count"
    ]:
        raise RuntimeError("Combined accepted and rejected counts do not reconcile")

    report = {
        "schema_version": "1.0",
        "pipeline_version": PIPELINE_VERSION,
        "dataset_version": COMBINED_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": RESIDUE_ANNOTATION_DATASET_VERSION,
        "source": {
            "path": _display_path(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "research_config": {
            "source": (
                _display_path(DEFAULT_CONFIG_PATH)
                if config is None
                else "provided ResearchConfig object"
            ),
            "sha256": (
                hashlib.sha256(DEFAULT_CONFIG_PATH.read_bytes()).hexdigest()
                if config is None
                else None
            ),
            "values": {
                "random_seed": active_config.random_seed,
                "sequence_min_length": active_config.sequence_min_length,
                "sequence_max_length": active_config.sequence_max_length,
                "redox_residues": list(active_config.redox_residues),
                "cd_hit_identity_threshold": active_config.cd_hit_identity_threshold,
                "primary_delta": active_config.primary_delta,
                "sensitivity_deltas": list(active_config.sensitivity_deltas),
                "pilot_dataset_size": active_config.pilot_dataset_size,
            },
        },
        "perturbation_schema": {
            "version": PERTURBATION_SCHEMA_VERSION,
            "path": _display_path(DEFAULT_SCHEMA_PATH),
            "sha256": hashlib.sha256(DEFAULT_SCHEMA_PATH.read_bytes()).hexdigest(),
        },
        "generator_dataset_versions": {
            "P1": P1_DATASET_VERSION,
            "P2": P2_DATASET_VERSION,
            "P3": P3_DATASET_VERSION,
        },
        "validation": {
            "mode": "source-linked structural and perturbation-specific semantic validation",
            "invalid_variant_action": "exclude_from_combined_output_and_record_in_rejection_ledger",
            "accepted_output_schema": list(PERTURBATION_FIELDS),
            "rejection_ledger_schema": list(REJECTION_FIELDS),
        },
        "counts": counts,
        "outputs": {
            "accepted_perturbations": _artifact(output_path, len(accepted)),
            "rejected_perturbations": _artifact(rejection_path, len(rejected)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_combined_perturbation_dataset()
    counts = report["counts"]
    print(
        f'Accepted {counts["accepted_variant_count"]} of '
        f'{counts["generated_variant_count"]} generated P1/P2/P3 variants; '
        f'rejected {counts["rejected_variant_count"]}.'
    )


if __name__ == "__main__":
    main()
