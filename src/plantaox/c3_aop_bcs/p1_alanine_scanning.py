"""Generate deterministic P1 alanine-scanning variants for Task 3.11."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .config import ResearchConfig, load_research_config
from .perturbation_schema import (
    DEFAULT_SCHEMA_PATH,
    PERTURBATION_FIELDS,
    PERTURBATION_SCHEMA_VERSION,
    PerturbationRecord,
)
from .residue_annotation import (
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
    / "p1_alanine_variants_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "p1_alanine_scanning_report_v1.json"
)
P1_DATASET_VERSION = "c3_aop_bcs_p1_alanine_v1"
ALANINE = "A"


def _variant_id(sequence_id: str, position: int, original_residue: str) -> str:
    return f"{sequence_id}-P1-{position:02d}-{original_residue}{ALANINE}"


def generate_p1_records(
    annotations: Iterable[Mapping[str, Any]],
    redox_residues: Sequence[str],
) -> list[PerturbationRecord]:
    """Create one independently validated alanine variant per redox position."""

    redox_set = frozenset(redox_residues)
    records: list[PerturbationRecord] = []
    seen_positions: set[tuple[str, int]] = set()

    for annotation in annotations:
        sequence_id = str(annotation.get("sequence_id") or "")
        sequence = str(annotation.get("peptide_sequence") or "")
        residue = str(annotation.get("residue") or "")
        residue_class = str(annotation.get("residue_class") or "")
        try:
            position = int(str(annotation.get("residue_position") or "0"))
        except ValueError as exc:
            raise ValueError(f"Invalid residue position for {sequence_id}") from exc

        if not sequence_id or not 1 <= position <= len(sequence):
            raise ValueError("Annotation contains an invalid sequence identifier or position")
        if sequence[position - 1] != residue:
            raise ValueError(f"Annotation residue mismatch for {sequence_id} at {position}")
        expected_class = REDOX_CLASS if residue in redox_set else "non_redox"
        if residue_class != expected_class:
            raise ValueError(f"Annotation class mismatch for {sequence_id} at {position}")

        key = (sequence_id, position)
        if key in seen_positions:
            raise ValueError(f"Duplicate annotation for {sequence_id} at {position}")
        seen_positions.add(key)
        if residue_class != REDOX_CLASS:
            continue

        perturbed = f"{sequence[: position - 1]}{ALANINE}{sequence[position:]}"
        records.append(
            PerturbationRecord(
                schema_version=PERTURBATION_SCHEMA_VERSION,
                variant_id=_variant_id(sequence_id, position, residue),
                sequence_id=sequence_id,
                original_sequence=sequence,
                position=position,
                original_residue=residue,
                substituted_residue=ALANINE,
                perturbed_sequence=perturbed,
                perturbation_type="P1",
            )
        )

    variant_ids = [record.variant_id for record in records]
    if len(variant_ids) != len(set(variant_ids)):
        raise RuntimeError("P1 generation produced duplicate variant identifiers")
    return records


def _read_annotations(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != ANNOTATION_FIELDS:
            raise ValueError("Input schema does not match the Task 3.9 annotation contract")
        return list(reader)


def _write_records(records: Sequence[PerturbationRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=PERTURBATION_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(record.as_dict() for record in records)


def _display_path(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix() if path.is_relative_to(REPOSITORY_ROOT) else str(path)


def _artifact(path: Path, record_count: int) -> dict[str, str | int]:
    return {
        "path": _display_path(path),
        "record_count": record_count,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_p1_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Build P1 variants and a versioned, checksum-backed generation report."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()
    annotations = _read_annotations(input_path)
    records = generate_p1_records(annotations, active_config.redox_residues)
    _write_records(records, output_path)

    source_sequence_ids = {str(row["sequence_id"]) for row in annotations}
    generated_sequence_ids = {record.sequence_id for record in records}
    per_residue = Counter(record.original_residue for record in records)
    counts = {
        "input_peptide_count": len(source_sequence_ids),
        "input_annotation_count": len(annotations),
        "input_redox_position_count": sum(
            str(row["residue_class"]) == REDOX_CLASS for row in annotations
        ),
        "peptides_with_variants": len(generated_sequence_ids),
        "generated_variant_count": len(records),
        "variants_by_original_residue": {
            residue: per_residue[residue] for residue in active_config.redox_residues
        },
    }
    if counts["input_redox_position_count"] != counts["generated_variant_count"]:
        raise RuntimeError("P1 output does not cover every redox position exactly once")
    if generated_sequence_ids != source_sequence_ids:
        raise RuntimeError("P1 output does not cover every eligible peptide")

    report = {
        "schema_version": "1.0",
        "dataset_version": P1_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": RESIDUE_ANNOTATION_DATASET_VERSION,
        "source": {
            "path": _display_path(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "perturbation_schema": {
            "version": PERTURBATION_SCHEMA_VERSION,
            "path": _display_path(DEFAULT_SCHEMA_PATH),
            "sha256": hashlib.sha256(DEFAULT_SCHEMA_PATH.read_bytes()).hexdigest(),
        },
        "p1_rule": {
            "eligible_original_residues": list(active_config.redox_residues),
            "substituted_residue": ALANINE,
            "one_position_per_variant": True,
            "preserve_sequence_length": True,
        },
        "counts": counts,
        "outputs": {
            "p1_variants": _artifact(output_path, len(records)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_p1_dataset()
    counts = report["counts"]
    print(
        f'Generated {counts["generated_variant_count"]} P1 alanine variants '
        f'across {counts["peptides_with_variants"]} peptides.'
    )


if __name__ == "__main__":
    main()
