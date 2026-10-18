"""Generate deterministic P2 BLOSUM62-conservative variants for Task 3.13."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .blosum62 import (
    Blosum62Matrix,
    DEFAULT_MANIFEST_PATH as BLOSUM62_MANIFEST_PATH,
    MINIMUM_CONSERVATIVE_SCORE,
    TIE_BREAK_RULE,
    load_blosum62,
    select_conservative_substitution,
)
from .config import ResearchConfig, load_research_config
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
    / "p2_conservative_variants_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "p2_conservative_substitutions_report_v1.json"
)
P2_DATASET_VERSION = "c3_aop_bcs_p2_conservative_v1"


def _variant_id(
    sequence_id: str,
    position: int,
    original_residue: str,
    substituted_residue: str,
) -> str:
    return (
        f"{sequence_id}-P2-{position:02d}-"
        f"{original_residue}{substituted_residue}"
    )


def generate_p2_records(
    annotations: Iterable[Mapping[str, Any]],
    matrix: Mapping[tuple[str, str], int],
    redox_residues: Sequence[str],
    minimum_score: int = MINIMUM_CONSERVATIVE_SCORE,
) -> list[PerturbationRecord]:
    """Create one conservative variant for each selectable non-redox position."""

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
        expected_class = REDOX_CLASS if residue in redox_set else NON_REDOX_CLASS
        if residue_class != expected_class:
            raise ValueError(f"Annotation class mismatch for {sequence_id} at {position}")

        key = (sequence_id, position)
        if key in seen_positions:
            raise ValueError(f"Duplicate annotation for {sequence_id} at {position}")
        seen_positions.add(key)
        if residue_class != NON_REDOX_CLASS:
            continue

        selection = select_conservative_substitution(
            residue,
            matrix,
            redox_residues,
            minimum_score,
        )
        if selection is None:
            continue

        perturbed = (
            f"{sequence[: position - 1]}{selection.residue}{sequence[position:]}"
        )
        records.append(
            PerturbationRecord(
                schema_version=PERTURBATION_SCHEMA_VERSION,
                variant_id=_variant_id(
                    sequence_id,
                    position,
                    residue,
                    selection.residue,
                ),
                sequence_id=sequence_id,
                original_sequence=sequence,
                position=position,
                original_residue=residue,
                substituted_residue=selection.residue,
                perturbed_sequence=perturbed,
                perturbation_type="P2",
                blosum62_score=selection.score,
            )
        )

    variant_ids = [record.variant_id for record in records]
    if len(variant_ids) != len(set(variant_ids)):
        raise RuntimeError("P2 generation produced duplicate variant identifiers")
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
        writer = csv.DictWriter(
            csv_file,
            fieldnames=PERTURBATION_FIELDS,
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


def build_p2_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    matrix: Blosum62Matrix | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Build P2 variants and a versioned, checksum-backed generation report."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()
    active_matrix = load_blosum62() if matrix is None else matrix
    annotations = _read_annotations(input_path)
    records = generate_p2_records(
        annotations,
        active_matrix,
        active_config.redox_residues,
    )
    _write_records(records, output_path)

    source_sequence_ids = {str(row["sequence_id"]) for row in annotations}
    generated_sequence_ids = {record.sequence_id for record in records}
    non_redox_annotations = [
        row for row in annotations if str(row["residue_class"]) == NON_REDOX_CLASS
    ]
    original_counts = Counter(str(row["residue"]) for row in non_redox_annotations)
    generated_original_counts = Counter(record.original_residue for record in records)
    substituted_counts = Counter(record.substituted_residue for record in records)
    skipped_counts = {
        residue: original_counts[residue] - generated_original_counts[residue]
        for residue in sorted(original_counts)
        if original_counts[residue] > generated_original_counts[residue]
    }
    counts = {
        "input_peptide_count": len(source_sequence_ids),
        "input_annotation_count": len(annotations),
        "input_non_redox_position_count": len(non_redox_annotations),
        "peptides_with_variants": len(generated_sequence_ids),
        "peptides_without_variants": len(source_sequence_ids - generated_sequence_ids),
        "generated_variant_count": len(records),
        "skipped_no_candidate_position_count": len(non_redox_annotations) - len(records),
        "variants_by_original_residue": {
            residue: generated_original_counts[residue]
            for residue in sorted(generated_original_counts)
        },
        "variants_by_substituted_residue": {
            residue: substituted_counts[residue]
            for residue in sorted(substituted_counts)
        },
        "skipped_no_candidate_by_original_residue": skipped_counts,
    }
    if (
        counts["generated_variant_count"]
        + counts["skipped_no_candidate_position_count"]
        != counts["input_non_redox_position_count"]
    ):
        raise RuntimeError("P2 generated and skipped position counts do not reconcile")

    report = {
        "schema_version": "1.0",
        "dataset_version": P2_DATASET_VERSION,
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
        "blosum62_support": {
            "path": _display_path(BLOSUM62_MANIFEST_PATH),
            "sha256": hashlib.sha256(BLOSUM62_MANIFEST_PATH.read_bytes()).hexdigest(),
        },
        "p2_rule": {
            "eligible_position_class": NON_REDOX_CLASS,
            "minimum_blosum62_score": MINIMUM_CONSERVATIVE_SCORE,
            "excluded_substitutions": [
                "original_residue",
                "A",
                *active_config.redox_residues,
            ],
            "tie_break": TIE_BREAK_RULE,
            "no_candidate_action": "skip_position",
            "one_position_per_variant": True,
            "preserve_sequence_length": True,
        },
        "counts": counts,
        "outputs": {
            "p2_variants": _artifact(output_path, len(records)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_p2_dataset()
    counts = report["counts"]
    print(
        f'Generated {counts["generated_variant_count"]} P2 conservative variants '
        f'across {counts["peptides_with_variants"]} peptides; skipped '
        f'{counts["skipped_no_candidate_position_count"]} non-redox positions '
        "without an eligible candidate."
    )


if __name__ == "__main__":
    main()
