"""Filter CD-HIT representatives for Task 3.8 redox eligibility."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .config import ResearchConfig, load_research_config
from .identity_deduplication import (
    CD_HIT_DATASET_VERSION,
    REPRESENTATIVE_FIELDS,
)
from .standardization import REPOSITORY_ROOT


DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "cd_hit_representatives_90_v1.csv"
)
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "redox_eligible_sequences_v1.csv"
)
DEFAULT_EXCLUSIONS_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "redox_eligibility_exclusions_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "redox_eligibility_report_v1.json"
)
REDOX_ELIGIBLE_DATASET_VERSION = "c3_aop_bcs_redox_eligible_v1"
EXCLUSION_REASON = "no_redox_residue"

OUTPUT_FIELDS = (
    *REPRESENTATIVE_FIELDS,
    "redox_residue_count",
    "redox_residues_present",
)
EXCLUSION_FIELDS = (*OUTPUT_FIELDS, "exclusion_reason")


def detect_redox_residues(
    sequence: str,
    redox_residues: Sequence[str],
) -> tuple[int, tuple[str, ...]]:
    """Return total redox-residue occurrences and present residues in config order."""

    configured = tuple(redox_residues)
    count = sum(sequence.count(residue) for residue in configured)
    present = tuple(residue for residue in configured if residue in sequence)
    return count, present


def filter_redox_eligible_records(
    records: Iterable[Mapping[str, Any]],
    redox_residues: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Split representative records by presence of at least one redox residue."""

    eligible: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    input_count = 0

    for source_record in records:
        input_count += 1
        record = dict(source_record)
        sequence = str(record.get("peptide_sequence") or "")
        count, present = detect_redox_residues(sequence, redox_residues)
        annotated = {
            **record,
            "redox_residue_count": count,
            "redox_residues_present": "".join(present),
        }
        if count:
            eligible.append(annotated)
        else:
            exclusions.append({**annotated, "exclusion_reason": EXCLUSION_REASON})

    counts = {
        "input_count": input_count,
        "eligible_count": len(eligible),
        "rejected_no_redox_residue_count": len(exclusions),
    }
    if counts["eligible_count"] + counts["rejected_no_redox_residue_count"] != input_count:
        raise RuntimeError("Redox eligibility counts do not reconcile with the input count")
    return eligible, exclusions, counts


def _read_representatives(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != REPRESENTATIVE_FIELDS:
            raise ValueError("Input schema does not match the Task 3.7 representative contract")
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


def build_redox_eligible_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    exclusions_path: str | Path = DEFAULT_EXCLUSIONS_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Create the final P1-eligible subject table, exclusions, and report."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    exclusions_path = Path(exclusions_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()
    records = _read_representatives(input_path)
    eligible, exclusions, counts = filter_redox_eligible_records(
        records,
        active_config.redox_residues,
    )

    _write_csv(eligible, output_path, OUTPUT_FIELDS)
    _write_csv(exclusions, exclusions_path, EXCLUSION_FIELDS)

    report = {
        "schema_version": "1.0",
        "dataset_version": REDOX_ELIGIBLE_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": CD_HIT_DATASET_VERSION,
        "source": {
            "path": _display_path(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "eligibility_rule": {
            "redox_residues": list(active_config.redox_residues),
            "minimum_required_occurrences": 1,
            "rejection_reason": EXCLUSION_REASON,
        },
        "counts": counts,
        "outputs": {
            "eligible": _artifact(output_path, len(eligible)),
            "exclusions": _artifact(exclusions_path, len(exclusions)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_redox_eligible_dataset()
    counts = report["counts"]
    print(
        f'Redox eligibility retained {counts["eligible_count"]} of '
        f'{counts["input_count"]} representatives and rejected '
        f'{counts["rejected_no_redox_residue_count"]}.'
    )


if __name__ == "__main__":
    main()
