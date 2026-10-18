"""Generate reproducible P3 random-control substitutions for Task 3.14."""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .config import STANDARD_AMINO_ACIDS, ResearchConfig, load_research_config
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
    / "p3_random_control_variants_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "p3_random_controls_report_v1.json"
)
P3_DATASET_VERSION = "c3_aop_bcs_p3_random_control_v1"
RANDOM_SELECTION_ALGORITHM = "sha256_modulo_v1"
SEED_MATERIAL_FIELDS = (
    "algorithm",
    "master_seed",
    "sequence_id",
    "original_sequence",
    "position",
    "original_residue",
)


@dataclass(frozen=True, slots=True)
class RandomSubstitutionChoice:
    """A deterministic pseudorandom replacement plus auditable metadata."""

    residue: str
    candidate_index: int
    candidate_count: int
    derived_seed_sha256: str


def random_substitution_metadata(choice: RandomSubstitutionChoice) -> str:
    """Serialize the auditable P3 choice metadata in canonical JSON form."""

    return json.dumps(
        {
            "candidate_count": choice.candidate_count,
            "candidate_index": choice.candidate_index,
            "derived_seed_sha256": choice.derived_seed_sha256,
            "selection_algorithm": RANDOM_SELECTION_ALGORITHM,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _validate_master_seed(master_seed: int) -> None:
    if (
        isinstance(master_seed, bool)
        or not isinstance(master_seed, int)
        or not 0 <= master_seed <= 2**32 - 1
    ):
        raise ValueError("master_seed must be an integer in the unsigned 32-bit range")


def select_random_substitution(
    sequence_id: str,
    original_sequence: str,
    position: int,
    original_residue: str,
    master_seed: int,
) -> RandomSubstitutionChoice:
    """Select one of the 19 alternatives using position-specific seed material."""

    _validate_master_seed(master_seed)
    if not sequence_id:
        raise ValueError("sequence_id must not be empty")
    if not original_sequence or set(original_sequence) - STANDARD_AMINO_ACIDS:
        raise ValueError("original_sequence must contain only standard amino acids")
    if isinstance(position, bool) or not isinstance(position, int):
        raise ValueError("position must be an integer")
    if not 1 <= position <= len(original_sequence):
        raise ValueError("position must use one-based indexing within original_sequence")
    if original_residue not in STANDARD_AMINO_ACIDS:
        raise ValueError("original_residue must be a standard amino acid")
    if original_sequence[position - 1] != original_residue:
        raise ValueError("original_residue does not match original_sequence at position")

    candidates = tuple(sorted(STANDARD_AMINO_ACIDS - {original_residue}))
    seed_material = {
        "algorithm": RANDOM_SELECTION_ALGORITHM,
        "master_seed": master_seed,
        "sequence_id": sequence_id,
        "original_sequence": original_sequence,
        "position": position,
        "original_residue": original_residue,
    }
    encoded = json.dumps(
        seed_material,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).digest()
    candidate_index = int.from_bytes(digest, byteorder="big") % len(candidates)
    return RandomSubstitutionChoice(
        residue=candidates[candidate_index],
        candidate_index=candidate_index,
        candidate_count=len(candidates),
        derived_seed_sha256=digest.hex(),
    )


def _variant_id(
    sequence_id: str,
    position: int,
    original_residue: str,
    substituted_residue: str,
) -> str:
    return (
        f"{sequence_id}-P3-{position:02d}-"
        f"{original_residue}{substituted_residue}"
    )


def generate_p3_records(
    annotations: Iterable[Mapping[str, Any]],
    redox_residues: Sequence[str],
    master_seed: int,
) -> list[PerturbationRecord]:
    """Create one reproducible random-control variant per annotated position."""

    _validate_master_seed(master_seed)
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

        choice = select_random_substitution(
            sequence_id,
            sequence,
            position,
            residue,
            master_seed,
        )
        perturbed = f"{sequence[: position - 1]}{choice.residue}{sequence[position:]}"
        random_metadata = random_substitution_metadata(choice)
        records.append(
            PerturbationRecord(
                schema_version=PERTURBATION_SCHEMA_VERSION,
                variant_id=_variant_id(
                    sequence_id,
                    position,
                    residue,
                    choice.residue,
                ),
                sequence_id=sequence_id,
                original_sequence=sequence,
                position=position,
                original_residue=residue,
                substituted_residue=choice.residue,
                perturbed_sequence=perturbed,
                perturbation_type="P3",
                random_seed=master_seed,
                random_metadata=random_metadata,
            )
        )

    variant_ids = [record.variant_id for record in records]
    if len(variant_ids) != len(set(variant_ids)):
        raise RuntimeError("P3 generation produced duplicate variant identifiers")
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


def build_p3_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Build P3 variants and a versioned, checksum-backed generation report."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()
    annotations = _read_annotations(input_path)
    records = generate_p3_records(
        annotations,
        active_config.redox_residues,
        active_config.random_seed,
    )
    _write_records(records, output_path)

    source_sequence_ids = {str(row["sequence_id"]) for row in annotations}
    generated_sequence_ids = {record.sequence_id for record in records}
    original_counts = Counter(record.original_residue for record in records)
    substituted_counts = Counter(record.substituted_residue for record in records)
    counts = {
        "input_peptide_count": len(source_sequence_ids),
        "input_annotation_count": len(annotations),
        "peptides_with_variants": len(generated_sequence_ids),
        "generated_variant_count": len(records),
        "variants_by_original_residue": {
            residue: original_counts[residue] for residue in sorted(original_counts)
        },
        "variants_by_substituted_residue": {
            residue: substituted_counts[residue]
            for residue in sorted(substituted_counts)
        },
    }
    if counts["generated_variant_count"] != counts["input_annotation_count"]:
        raise RuntimeError("P3 output does not cover every annotated position exactly once")
    if generated_sequence_ids != source_sequence_ids:
        raise RuntimeError("P3 output does not cover every eligible peptide")

    report = {
        "schema_version": "1.0",
        "dataset_version": P3_DATASET_VERSION,
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
        "p3_rule": {
            "master_random_seed": active_config.random_seed,
            "selection_algorithm": RANDOM_SELECTION_ALGORITHM,
            "seed_material_fields": list(SEED_MATERIAL_FIELDS),
            "seed_material_encoding": "canonical sorted-key compact JSON encoded as UTF-8",
            "candidate_order": "alphabetical standard amino acids excluding original residue",
            "candidate_count_per_position": len(STANDARD_AMINO_ACIDS) - 1,
            "one_position_per_variant": True,
            "preserve_sequence_length": True,
        },
        "counts": counts,
        "outputs": {
            "p3_variants": _artifact(output_path, len(records)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_p3_dataset()
    counts = report["counts"]
    print(
        f'Generated {counts["generated_variant_count"]} P3 random-control variants '
        f'across {counts["peptides_with_variants"]} peptides using master seed '
        f'{report["p3_rule"]["master_random_seed"]}.'
    )


if __name__ == "__main__":
    main()
