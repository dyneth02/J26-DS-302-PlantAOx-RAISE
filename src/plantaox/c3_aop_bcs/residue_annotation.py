"""Create deterministic residue-level annotations for Task 3.9."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .config import ResearchConfig, load_research_config
from .redox_eligibility import (
    OUTPUT_FIELDS as ELIGIBLE_FIELDS,
    REDOX_ELIGIBLE_DATASET_VERSION,
)
from .standardization import REPOSITORY_ROOT


DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "redox_eligible_sequences_v1.csv"
)
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "residue_annotations_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "residue_annotation_report_v1.json"
)
RESIDUE_ANNOTATION_DATASET_VERSION = "c3_aop_bcs_residue_annotations_v1"
REDOX_CLASS = "redox"
NON_REDOX_CLASS = "non_redox"

OUTPUT_FIELDS = (
    *ELIGIBLE_FIELDS,
    "residue_position",
    "residue",
    "residue_class",
    "peptide_redox_position_count",
)


def annotate_residue_positions(
    records: Iterable[Mapping[str, Any]],
    redox_residues: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Expand peptide records into complete, one-based residue annotations."""

    redox_set = frozenset(redox_residues)
    annotations: list[dict[str, Any]] = []
    peptide_count = 0
    redox_position_count = 0

    for source_record in records:
        peptide_count += 1
        record = dict(source_record)
        sequence_id = str(record.get("sequence_id") or "")
        sequence = str(record.get("peptide_sequence") or "")
        if not sequence_id or not sequence:
            raise ValueError("Eligible input contains a missing sequence identifier or sequence")

        expected_length = int(str(record.get("sequence_length") or "0"))
        if expected_length != len(sequence):
            raise ValueError(f"Sequence length mismatch for {sequence_id}")

        peptide_redox_count = sum(residue in redox_set for residue in sequence)
        source_redox_count = int(str(record.get("redox_residue_count") or "0"))
        if peptide_redox_count == 0:
            raise ValueError(f"Task 3.8 input contains an ineligible sequence: {sequence_id}")
        if peptide_redox_count != source_redox_count:
            raise ValueError(f"Redox count mismatch for {sequence_id}")

        redox_position_count += peptide_redox_count
        for position, residue in enumerate(sequence, start=1):
            annotations.append(
                {
                    **record,
                    "residue_position": position,
                    "residue": residue,
                    "residue_class": REDOX_CLASS if residue in redox_set else NON_REDOX_CLASS,
                    "peptide_redox_position_count": peptide_redox_count,
                }
            )

    annotation_count = len(annotations)
    counts = {
        "peptide_count": peptide_count,
        "annotation_count": annotation_count,
        "redox_position_count": redox_position_count,
        "non_redox_position_count": annotation_count - redox_position_count,
    }
    if counts["redox_position_count"] + counts["non_redox_position_count"] != annotation_count:
        raise RuntimeError("Residue annotation counts do not reconcile")
    return annotations, counts


def _read_eligible_records(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != ELIGIBLE_FIELDS:
            raise ValueError("Input schema does not match the Task 3.8 eligible-subject contract")
        return list(reader)


def _write_csv(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
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


def build_residue_annotation_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Generate the Task 3.9 residue table and its reproducibility report."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()
    records = _read_eligible_records(input_path)
    annotations, counts = annotate_residue_positions(records, active_config.redox_residues)
    _write_csv(annotations, output_path)

    report = {
        "schema_version": "1.0",
        "dataset_version": RESIDUE_ANNOTATION_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": REDOX_ELIGIBLE_DATASET_VERSION,
        "source": {
            "path": _display_path(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "annotation_rule": {
            "position_index_base": 1,
            "redox_residues": list(active_config.redox_residues),
            "redox_class": REDOX_CLASS,
            "non_redox_class": NON_REDOX_CLASS,
        },
        "counts": counts,
        "outputs": {
            "residue_annotations": _artifact(output_path, len(annotations)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_residue_annotation_dataset()
    counts = report["counts"]
    print(
        f'Annotated {counts["annotation_count"]} residue positions across '
        f'{counts["peptide_count"]} eligible peptides, including '
        f'{counts["redox_position_count"]} redox positions.'
    )


if __name__ == "__main__":
    main()
