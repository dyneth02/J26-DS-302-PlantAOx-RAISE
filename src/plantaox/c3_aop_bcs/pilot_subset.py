"""Deterministic PP1 pilot-subset selection for Task 3.25."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .config import ResearchConfig, load_research_config
from .perturbation_schema import PERTURBATION_FIELDS, PerturbationRecord
from .standardization import REPOSITORY_ROOT


PILOT_SCHEMA_VERSION = "1.0"
PILOT_DATASET_VERSION = "c3_aop_bcs_pp1_pilot_v1"
PILOT_SELECTION_ALGORITHM = "greedy_coverage_then_seeded_sha256_v1"

DEFAULT_SUBJECT_INPUT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "redox_eligible_sequences_v1.csv"
)
DEFAULT_PERTURBATION_INPUT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "combined_perturbations_v1.csv"
)
DEFAULT_SUBJECT_OUTPUT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "pp1_pilot_subjects_v1.csv"
)
DEFAULT_PERTURBATION_OUTPUT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "pp1_pilot_perturbations_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "pp1_pilot_report_v1.json"
)

SUBJECT_SOURCE_FIELDS = (
    "sequence_id",
    "peptide_sequence",
    "source",
    "source_record_id",
    "evidence_tier_candidate",
    "evidence_basis",
    "source_reference",
    "source_label",
    "frs",
    "chelator",
    "raw_file",
    "raw_row_number",
    "sequence_length",
    "cd_hit_cluster_id",
    "cd_hit_cluster_size",
    "redox_residue_count",
    "redox_residues_present",
)
PILOT_METADATA_FIELDS = (
    "pilot_schema_version",
    "pilot_dataset_version",
    "selection_rank",
    "selection_seed",
    "selection_key_sha256",
    "length_band",
    "redox_pattern_type",
    "new_core_coverage_at_selection",
)
PILOT_SUBJECT_FIELDS = (*PILOT_METADATA_FIELDS, *SUBJECT_SOURCE_FIELDS)
LENGTH_BANDS = (
    ("short_3_10", 3, 10),
    ("medium_11_20", 11, 20),
    ("long_21_35", 21, 35),
    ("very_long_36_50", 36, 50),
)


class PilotSubsetError(ValueError):
    """Raised when pilot selection inputs or outputs violate the contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _length_band(length: int) -> str:
    for label, minimum, maximum in LENGTH_BANDS:
        if minimum <= length <= maximum:
            return label
    raise PilotSubsetError(f"sequence length {length} is outside the configured pilot bands")


def _selection_key(row: Mapping[str, str], seed: int) -> str:
    payload = "\0".join(
        (
            PILOT_SELECTION_ALGORITHM,
            str(seed),
            row["sequence_id"],
            row["peptide_sequence"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_subjects(path: Path, config: ResearchConfig) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != SUBJECT_SOURCE_FIELDS:
            raise PilotSubsetError("pilot subject input schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise PilotSubsetError("pilot subject input is empty")
    if len({row["sequence_id"] for row in rows}) != len(rows):
        raise PilotSubsetError("pilot subject input has duplicate sequence identifiers")
    for row in rows:
        sequence = row["peptide_sequence"]
        if int(row["sequence_length"]) != len(sequence):
            raise PilotSubsetError(f"{row['sequence_id']} has an invalid sequence length")
        expected_pattern = "".join(residue for residue in config.redox_residues if residue in sequence)
        if row["redox_residues_present"] != expected_pattern:
            raise PilotSubsetError(f"{row['sequence_id']} has inconsistent redox metadata")
    return rows


def _read_perturbations(path: Path) -> list[PerturbationRecord]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != PERTURBATION_FIELDS:
            raise PilotSubsetError("pilot perturbation input schema is invalid")
        rows = [PerturbationRecord.from_mapping(row) for row in reader]
    if len({row.variant_id for row in rows}) != len(rows):
        raise PilotSubsetError("pilot perturbation input has duplicate variant identifiers")
    return rows


def _core_tokens(
    row: Mapping[str, str],
    variant_types: Mapping[str, set[str]],
) -> set[str]:
    pattern = row["redox_residues_present"]
    tokens = {f"length:{_length_band(int(row['sequence_length']))}"}
    tokens.update(f"redox:{residue}" for residue in pattern)
    tokens.add("pattern:single_type" if len(pattern) == 1 else "pattern:multiple_types")
    tokens.update(f"variant:{kind}" for kind in variant_types.get(row["sequence_id"], set()))
    return tokens


def select_pilot_subjects(
    candidates: Sequence[Mapping[str, str]],
    variant_types: Mapping[str, set[str]],
    config: ResearchConfig,
) -> list[dict[str, str]]:
    """Select a row-order-independent pilot using coverage and seeded hashes."""

    if not 10 <= config.pilot_dataset_size <= 30:
        raise PilotSubsetError("PP1 pilot_dataset_size must remain within 10-30")
    if len(candidates) < config.pilot_dataset_size:
        raise PilotSubsetError("not enough candidates for the configured pilot size")

    available_core = set().union(
        *(_core_tokens(row, variant_types) for row in candidates)
    )
    selected: list[dict[str, str]] = []
    remaining = [dict(row) for row in candidates]
    covered_core: set[str] = set()
    covered_patterns: set[str] = set()
    covered_sources: set[str] = set()
    covered_evidence: set[str] = set()

    while len(selected) < config.pilot_dataset_size:
        ranked: list[tuple[tuple[object, ...], dict[str, str], set[str]]] = []
        for row in remaining:
            core = _core_tokens(row, variant_types)
            new_core = core - covered_core
            pattern = row["redox_residues_present"]
            key = _selection_key(row, config.random_seed)
            priority = (
                -len(new_core),
                -(pattern not in covered_patterns),
                -(row["source"] not in covered_sources),
                -(row["evidence_tier_candidate"] not in covered_evidence),
                -(row["evidence_tier_candidate"] == "E1"),
                key,
                row["sequence_id"],
            )
            ranked.append((priority, row, new_core))
        _, chosen, new_core = min(ranked, key=lambda item: item[0])
        remaining.remove(chosen)
        covered_core.update(_core_tokens(chosen, variant_types))
        covered_patterns.add(chosen["redox_residues_present"])
        covered_sources.add(chosen["source"])
        covered_evidence.add(chosen["evidence_tier_candidate"])
        selected.append(
            {
                **chosen,
                "pilot_schema_version": PILOT_SCHEMA_VERSION,
                "pilot_dataset_version": PILOT_DATASET_VERSION,
                "selection_rank": str(len(selected) + 1),
                "selection_seed": str(config.random_seed),
                "selection_key_sha256": _selection_key(chosen, config.random_seed),
                "length_band": _length_band(int(chosen["sequence_length"])),
                "redox_pattern_type": (
                    "single_type" if len(chosen["redox_residues_present"]) == 1 else "multiple_types"
                ),
                "new_core_coverage_at_selection": json.dumps(
                    sorted(new_core), separators=(",", ":")
                ),
            }
        )

    if not available_core.issubset(covered_core):
        missing = sorted(available_core - covered_core)
        raise PilotSubsetError(f"configured pilot did not cover available core strata: {missing}")
    return selected


def _write_subjects(path: Path, rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=PILOT_SUBJECT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in PILOT_SUBJECT_FIELDS})


def _write_perturbations(path: Path, rows: Iterable[PerturbationRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=PERTURBATION_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(row.as_dict() for row in rows)


def build_pp1_pilot_subset(
    subject_input_path: str | Path = DEFAULT_SUBJECT_INPUT_PATH,
    perturbation_input_path: str | Path = DEFAULT_PERTURBATION_INPUT_PATH,
    subject_output_path: str | Path = DEFAULT_SUBJECT_OUTPUT_PATH,
    perturbation_output_path: str | Path = DEFAULT_PERTURBATION_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Select, validate, and export the versioned PP1 pilot artifacts."""

    active_config = config or load_research_config()
    subject_input = Path(subject_input_path)
    perturbation_input = Path(perturbation_input_path)
    subject_output = Path(subject_output_path)
    perturbation_output = Path(perturbation_output_path)
    report_output = Path(report_path)

    subjects = _read_subjects(subject_input, active_config)
    perturbations = _read_perturbations(perturbation_input)
    variants_by_sequence: dict[str, set[str]] = defaultdict(set)
    for record in perturbations:
        variants_by_sequence[record.sequence_id].add(record.perturbation_type)

    selected = select_pilot_subjects(subjects, variants_by_sequence, active_config)
    selected_by_id = {row["sequence_id"]: row for row in selected}
    selected_rank = {row["sequence_id"]: int(row["selection_rank"]) for row in selected}
    pilot_perturbations = [
        record for record in perturbations if record.sequence_id in selected_by_id
    ]
    type_order = {"P1": 1, "P2": 2, "P3": 3}
    pilot_perturbations.sort(
        key=lambda record: (
            selected_rank[record.sequence_id],
            type_order[record.perturbation_type],
            record.position,
            record.variant_id,
        )
    )
    for record in pilot_perturbations:
        if record.original_sequence != selected_by_id[record.sequence_id]["peptide_sequence"]:
            raise PilotSubsetError(f"{record.variant_id} does not match its selected subject")

    _write_subjects(subject_output, selected)
    _write_perturbations(perturbation_output, pilot_perturbations)

    length_counts = Counter(row["length_band"] for row in selected)
    redox_counts = {
        residue: sum(residue in row["redox_residues_present"] for row in selected)
        for residue in active_config.redox_residues
    }
    type_counts = Counter(record.perturbation_type for record in pilot_perturbations)
    report: dict[str, Any] = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "dataset_version": PILOT_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "selection": {
            "algorithm": PILOT_SELECTION_ALGORITHM,
            "master_seed": active_config.random_seed,
            "configured_size": active_config.pilot_dataset_size,
            "tie_break": "ascending SHA-256 over algorithm, seed, sequence_id, and sequence",
            "core_coverage": [
                "all available fixed length bands",
                "each configured redox residue",
                "single-type and multiple-type redox patterns",
                "all perturbation types available in the source",
            ],
            "secondary_diversity": [
                "distinct exact redox-residue patterns",
                "source datasets",
                "evidence tiers",
                "prefer E1 direct-assay evidence after coverage priorities",
            ],
            "row_order_independent": True,
            "purpose": "small reproducible PP1 workflow demonstration, not final-study sampling",
        },
        "sources": {
            "subjects": {
                "path": _display_path(subject_input),
                "dataset_version": "c3_aop_bcs_redox_eligible_v1",
                "record_count": len(subjects),
                "sha256": _sha256(subject_input),
            },
            "perturbations": {
                "path": _display_path(perturbation_input),
                "dataset_version": "c3_aop_bcs_combined_perturbations_v1",
                "record_count": len(perturbations),
                "sha256": _sha256(perturbation_input),
            },
        },
        "coverage": {
            "selected_subject_count": len(selected),
            "sequence_length_min": min(int(row["sequence_length"]) for row in selected),
            "sequence_length_max": max(int(row["sequence_length"]) for row in selected),
            "distinct_sequence_lengths": len({row["sequence_length"] for row in selected}),
            "length_band_counts": {
                label: length_counts[label] for label, _, _ in LENGTH_BANDS
            },
            "redox_residue_subject_counts": redox_counts,
            "redox_pattern_type_counts": dict(
                sorted(Counter(row["redox_pattern_type"] for row in selected).items())
            ),
            "distinct_redox_patterns": sorted(
                {row["redox_residues_present"] for row in selected}
            ),
            "source_counts": dict(sorted(Counter(row["source"] for row in selected).items())),
            "evidence_tier_counts": dict(
                sorted(Counter(row["evidence_tier_candidate"] for row in selected).items())
            ),
            "perturbation_count": len(pilot_perturbations),
            "perturbations_by_type": {
                kind: type_counts[kind] for kind in ("P1", "P2", "P3")
            },
        },
        "validation": {
            "status": "PASS",
            "size_within_10_to_30": 10 <= len(selected) <= 30,
            "configured_size_met": len(selected) == active_config.pilot_dataset_size,
            "all_redox_residues_represented": all(redox_counts.values()),
            "multiple_length_bands_represented": sum(bool(count) for count in length_counts.values()) > 1,
            "single_and_multiple_redox_patterns_represented": {
                row["redox_pattern_type"] for row in selected
            } == {"single_type", "multiple_types"},
            "all_three_perturbation_types_represented": all(type_counts[kind] for kind in ("P1", "P2", "P3")),
        },
        "outputs": {
            "subjects": {
                "path": _display_path(subject_output),
                "record_count": len(selected),
                "fields": list(PILOT_SUBJECT_FIELDS),
                "sha256": _sha256(subject_output),
            },
            "perturbations": {
                "path": _display_path(perturbation_output),
                "record_count": len(pilot_perturbations),
                "fields": list(PERTURBATION_FIELDS),
                "sha256": _sha256(perturbation_output),
            },
        },
    }
    if not all(report["validation"].values()):
        raise PilotSubsetError("pilot subset failed one or more validation checks")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


if __name__ == "__main__":
    result = build_pp1_pilot_subset()
    print(
        f"Selected {result['coverage']['selected_subject_count']} PP1 subjects with "
        f"{result['coverage']['perturbation_count']} perturbations."
    )
