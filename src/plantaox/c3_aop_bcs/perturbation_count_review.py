"""PP1 pilot perturbation-count quality review for Task 3.32."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from .blosum62 import load_blosum62, select_conservative_substitution
from .config import ResearchConfig, load_research_config
from .perturbation_schema import (
    PERTURBATION_FIELDS,
    PERTURBATION_TYPES,
    PerturbationRecord,
)
from .pilot_subset import (
    PILOT_DATASET_VERSION,
    PILOT_SUBJECT_FIELDS,
    DEFAULT_PERTURBATION_OUTPUT_PATH as DEFAULT_PERTURBATION_INPUT_PATH,
    DEFAULT_SUBJECT_OUTPUT_PATH as DEFAULT_SUBJECT_INPUT_PATH,
)
from .standardization import REPOSITORY_ROOT


COUNT_REVIEW_SCHEMA_VERSION = "1.0"
COUNT_REVIEW_PIPELINE_VERSION = "c3_aop_bcs_perturbation_count_review_v1"
COUNT_REVIEW_DATASET_VERSION = "c3_aop_bcs_pp1_pilot_perturbation_counts_v1"
DOMINANCE_THRESHOLD_FRACTION = 0.20

DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_perturbation_counts_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_perturbation_count_report_v1.json"
)

COUNT_REVIEW_FIELDS = (
    "count_review_schema_version",
    "count_review_dataset_version",
    "sequence_id",
    "selection_rank",
    "sequence_length",
    "redox_residue_count",
    "expected_p1_count",
    "actual_p1_count",
    "expected_p2_count",
    "actual_p2_count",
    "expected_p3_count",
    "actual_p3_count",
    "total_variant_count",
    "total_variant_share",
    "relative_to_equal_share",
    "expected_zero_types",
    "unexpected_zero_types",
    "counts_match_expected",
    "is_dominant",
)


class PerturbationCountReviewError(ValueError):
    """Raised when pilot count inputs or summaries violate the review contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _read_subjects(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != PILOT_SUBJECT_FIELDS:
            raise PerturbationCountReviewError("pilot subject schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise PerturbationCountReviewError("pilot subject input is empty")
    identifiers = [row["sequence_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise PerturbationCountReviewError("pilot subjects contain duplicate identifiers")
    return rows


def _read_perturbations(path: Path) -> list[PerturbationRecord]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != PERTURBATION_FIELDS:
            raise PerturbationCountReviewError("pilot perturbation schema is invalid")
        rows = [PerturbationRecord.from_mapping(row) for row in reader]
    if not rows:
        raise PerturbationCountReviewError("pilot perturbation input is empty")
    identifiers = [row.variant_id for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise PerturbationCountReviewError(
            "pilot perturbations contain duplicate variant identifiers"
        )
    return rows


def review_perturbation_counts(
    subjects: Sequence[Mapping[str, str]],
    perturbations: Sequence[PerturbationRecord],
    config: ResearchConfig,
    dominance_threshold: float = DOMINANCE_THRESHOLD_FRACTION,
) -> list[dict[str, str]]:
    """Build deterministic per-sequence expected/actual count diagnostics."""

    if not 0.0 < dominance_threshold <= 1.0:
        raise PerturbationCountReviewError("dominance threshold must be in (0,1]")
    if not subjects:
        raise PerturbationCountReviewError("count review requires at least one subject")
    subject_by_id = {row["sequence_id"]: row for row in subjects}
    if len(subject_by_id) != len(subjects):
        raise PerturbationCountReviewError("subjects contain duplicate identifiers")

    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in perturbations:
        subject = subject_by_id.get(record.sequence_id)
        if subject is None:
            raise PerturbationCountReviewError(
                f"{record.variant_id} refers to an unselected subject"
            )
        if record.original_sequence != subject["peptide_sequence"]:
            raise PerturbationCountReviewError(
                f"{record.variant_id} does not match its pilot subject sequence"
            )
        counts[record.sequence_id][record.perturbation_type] += 1

    matrix = load_blosum62()
    total_variants = len(perturbations)
    equal_share = 1.0 / len(subjects)
    output: list[dict[str, str]] = []
    for subject in sorted(subjects, key=lambda row: int(row["selection_rank"])):
        sequence_id = subject["sequence_id"]
        sequence = subject["peptide_sequence"]
        if int(subject["sequence_length"]) != len(sequence):
            raise PerturbationCountReviewError(
                f"{sequence_id} has inconsistent sequence length metadata"
            )
        expected = {
            "P1": sum(residue in config.redox_residues for residue in sequence),
            "P2": sum(
                residue not in config.redox_residues
                and select_conservative_substitution(
                    residue,
                    matrix,
                    config.redox_residues,
                )
                is not None
                for residue in sequence
            ),
            "P3": len(sequence),
        }
        actual = {kind: counts[sequence_id][kind] for kind in PERTURBATION_TYPES}
        total = sum(actual.values())
        share = total / total_variants
        expected_zero = [kind for kind in PERTURBATION_TYPES if expected[kind] == 0]
        unexpected_zero = [
            kind
            for kind in PERTURBATION_TYPES
            if expected[kind] > 0 and actual[kind] == 0
        ]
        output.append(
            {
                "count_review_schema_version": COUNT_REVIEW_SCHEMA_VERSION,
                "count_review_dataset_version": COUNT_REVIEW_DATASET_VERSION,
                "sequence_id": sequence_id,
                "selection_rank": subject["selection_rank"],
                "sequence_length": subject["sequence_length"],
                "redox_residue_count": subject["redox_residue_count"],
                "expected_p1_count": str(expected["P1"]),
                "actual_p1_count": str(actual["P1"]),
                "expected_p2_count": str(expected["P2"]),
                "actual_p2_count": str(actual["P2"]),
                "expected_p3_count": str(expected["P3"]),
                "actual_p3_count": str(actual["P3"]),
                "total_variant_count": str(total),
                "total_variant_share": repr(share),
                "relative_to_equal_share": repr(share / equal_share),
                "expected_zero_types": ";".join(expected_zero),
                "unexpected_zero_types": ";".join(unexpected_zero),
                "counts_match_expected": str(actual == expected).lower(),
                "is_dominant": str(share > dominance_threshold).lower(),
            }
        )
    return output


def _write_rows(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=COUNT_REVIEW_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows({field: row[field] for field in COUNT_REVIEW_FIELDS} for row in rows)


def build_perturbation_count_review(
    subject_path: str | Path = DEFAULT_SUBJECT_INPUT_PATH,
    perturbation_path: str | Path = DEFAULT_PERTURBATION_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Review PP1 pilot perturbation counts and export traceable QC artifacts."""

    active_config = config or load_research_config()
    subject_source = Path(subject_path)
    perturbation_source = Path(perturbation_path)
    output = Path(output_path)
    report_output = Path(report_path)
    subjects = _read_subjects(subject_source)
    perturbations = _read_perturbations(perturbation_source)
    summary_rows = review_perturbation_counts(
        subjects,
        perturbations,
        active_config,
    )
    _write_rows(output, summary_rows)

    type_counts = Counter(record.perturbation_type for record in perturbations)
    total_counts = [int(row["total_variant_count"]) for row in summary_rows]
    dominant_rows = [row for row in summary_rows if row["is_dominant"] == "true"]
    unexpected_zero_rows = [
        {
            "sequence_id": row["sequence_id"],
            "perturbation_types": row["unexpected_zero_types"].split(";"),
        }
        for row in summary_rows
        if row["unexpected_zero_types"]
    ]
    expected_zero_rows = [
        {
            "sequence_id": row["sequence_id"],
            "perturbation_types": row["expected_zero_types"].split(";"),
            "reason": (
                "the sequence has no position eligible under the frozen generator rules"
            ),
        }
        for row in summary_rows
        if row["expected_zero_types"]
    ]
    maximum_row = max(
        summary_rows,
        key=lambda row: (int(row["total_variant_count"]), row["sequence_id"]),
    )
    report: dict[str, Any] = {
        "schema_version": COUNT_REVIEW_SCHEMA_VERSION,
        "pipeline_version": COUNT_REVIEW_PIPELINE_VERSION,
        "dataset_version": COUNT_REVIEW_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "review_scope": {
            "pilot_dataset_version": PILOT_DATASET_VERSION,
            "purpose": "PP1 perturbation-count quality control",
            "dominance_rule": "total_variant_share > 0.20",
            "dominance_threshold_fraction": DOMINANCE_THRESHOLD_FRACTION,
            "dominance_threshold_note": (
                "Pragmatic PP1 QC flag, not an inferential or biological cutoff."
            ),
        },
        "sources": {
            "subjects": {
                "path": _display_path(subject_source),
                "record_count": len(subjects),
                "sha256": _sha256(subject_source),
            },
            "perturbations": {
                "path": _display_path(perturbation_source),
                "record_count": len(perturbations),
                "sha256": _sha256(perturbation_source),
            },
        },
        "counts": {
            "subject_count": len(subjects),
            "total_variant_count": len(perturbations),
            "by_perturbation_type": {
                kind: type_counts[kind] for kind in PERTURBATION_TYPES
            },
            "per_subject_minimum": min(total_counts),
            "per_subject_median": median(total_counts),
            "per_subject_maximum": max(total_counts),
        },
        "zero_variant_review": {
            "unexpected_cases": unexpected_zero_rows,
            "expected_not_applicable_cases": expected_zero_rows,
        },
        "dominance_review": {
            "dominant_sequence_count": len(dominant_rows),
            "dominant_sequence_ids": [row["sequence_id"] for row in dominant_rows],
            "maximum_contributor": {
                "sequence_id": maximum_row["sequence_id"],
                "variant_count": int(maximum_row["total_variant_count"]),
                "variant_share": float(maximum_row["total_variant_share"]),
                "relative_to_equal_share": float(
                    maximum_row["relative_to_equal_share"]
                ),
            },
        },
        "validation": {
            "status": "PASS",
            "all_three_types_nonzero": all(type_counts[kind] > 0 for kind in PERTURBATION_TYPES),
            "global_counts_reconcile": sum(type_counts.values()) == len(perturbations),
            "all_subjects_have_variants": all(total > 0 for total in total_counts),
            "per_subject_counts_match_generator_rules": all(
                row["counts_match_expected"] == "true" for row in summary_rows
            ),
            "no_unexpected_zero_variant_cases": not unexpected_zero_rows,
            "no_sequence_exceeds_dominance_threshold": not dominant_rows,
        },
        "output": {
            "path": _display_path(output),
            "record_count": len(summary_rows),
            "fields": list(COUNT_REVIEW_FIELDS),
            "sha256": _sha256(output),
        },
    }
    if not all(value for key, value in report["validation"].items() if key != "status"):
        raise PerturbationCountReviewError("perturbation-count review failed validation")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    result = build_perturbation_count_review()
    counts = result["counts"]
    maximum = result["dominance_review"]["maximum_contributor"]
    print(
        f"Reviewed {counts['total_variant_count']} pilot variants: "
        f"P1={counts['by_perturbation_type']['P1']}, "
        f"P2={counts['by_perturbation_type']['P2']}, "
        f"P3={counts['by_perturbation_type']['P3']}."
    )
    print(
        f"Largest contributor {maximum['sequence_id']} supplies "
        f"{maximum['variant_share']:.2%}; dominance check passed."
    )
