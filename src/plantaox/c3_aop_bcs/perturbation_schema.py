"""Frozen shared perturbation-record schema for Task 3.10."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .config import STANDARD_AMINO_ACIDS


PERTURBATION_SCHEMA_VERSION = "1.0"
PERTURBATION_TYPES = ("P1", "P2", "P3")
PERTURBATION_FIELDS = (
    "schema_version",
    "variant_id",
    "sequence_id",
    "original_sequence",
    "position",
    "original_residue",
    "substituted_residue",
    "perturbed_sequence",
    "perturbation_type",
    "blosum62_score",
    "random_seed",
    "random_metadata",
)
DEFAULT_SCHEMA_PATH = Path(__file__).with_name("perturbation_schema_v1.json")


def _parse_required_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        try:
            parsed = int(stripped)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer") from exc
        if stripped not in {str(parsed), f"+{parsed}"}:
            raise ValueError(f"{field_name} must be an integer")
        return parsed
    raise ValueError(f"{field_name} must be an integer")


def _parse_optional_integer(value: object, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    return _parse_required_integer(value, field_name)


def _canonical_random_metadata(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("random_metadata must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError("random_metadata must be a JSON object")
    return json.dumps(parsed, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class PerturbationRecord:
    """One validated, single-position peptide substitution."""

    schema_version: str
    variant_id: str
    sequence_id: str
    original_sequence: str
    position: int
    original_residue: str
    substituted_residue: str
    perturbed_sequence: str
    perturbation_type: str
    blosum62_score: int | None = None
    random_seed: int | None = None
    random_metadata: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != PERTURBATION_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {PERTURBATION_SCHEMA_VERSION!r}"
            )
        if not self.variant_id or not self.sequence_id:
            raise ValueError("variant_id and sequence_id must not be empty")
        if not self.original_sequence or not self.perturbed_sequence:
            raise ValueError("original_sequence and perturbed_sequence must not be empty")
        if set(self.original_sequence) - STANDARD_AMINO_ACIDS:
            raise ValueError("original_sequence contains a non-standard amino acid")
        if set(self.perturbed_sequence) - STANDARD_AMINO_ACIDS:
            raise ValueError("perturbed_sequence contains a non-standard amino acid")
        if len(self.original_residue) != 1 or self.original_residue not in STANDARD_AMINO_ACIDS:
            raise ValueError("original_residue must be one standard amino-acid symbol")
        if (
            len(self.substituted_residue) != 1
            or self.substituted_residue not in STANDARD_AMINO_ACIDS
        ):
            raise ValueError("substituted_residue must be one standard amino-acid symbol")
        if self.original_residue == self.substituted_residue:
            raise ValueError("substituted_residue must differ from original_residue")
        if isinstance(self.position, bool) or not isinstance(self.position, int):
            raise ValueError("position must be an integer")
        if not 1 <= self.position <= len(self.original_sequence):
            raise ValueError("position must use one-based indexing within original_sequence")
        if len(self.original_sequence) != len(self.perturbed_sequence):
            raise ValueError("perturbed_sequence must preserve sequence length")
        if self.original_sequence[self.position - 1] != self.original_residue:
            raise ValueError("original_residue does not match original_sequence at position")
        if self.perturbed_sequence[self.position - 1] != self.substituted_residue:
            raise ValueError("substituted_residue does not match perturbed_sequence at position")

        changed_positions = [
            index
            for index, (original, perturbed) in enumerate(
                zip(self.original_sequence, self.perturbed_sequence),
                start=1,
            )
            if original != perturbed
        ]
        if changed_positions != [self.position]:
            raise ValueError("each perturbation record must represent exactly one declared edit")
        if self.perturbation_type not in PERTURBATION_TYPES:
            raise ValueError(f"perturbation_type must be one of {PERTURBATION_TYPES}")

        canonical_metadata = _canonical_random_metadata(self.random_metadata)
        object.__setattr__(self, "random_metadata", canonical_metadata)
        if self.blosum62_score is not None and (
            isinstance(self.blosum62_score, bool)
            or not isinstance(self.blosum62_score, int)
        ):
            raise ValueError("blosum62_score must be an integer when present")
        if self.random_seed is not None and (
            isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int)
        ):
            raise ValueError("random_seed must be an integer when present")

        if self.perturbation_type == "P1":
            if any(
                value is not None
                for value in (self.blosum62_score, self.random_seed, self.random_metadata)
            ):
                raise ValueError("P1 records must not contain P2 or P3 metadata")
        elif self.perturbation_type == "P2":
            if self.blosum62_score is None:
                raise ValueError("P2 records require blosum62_score")
            if self.random_seed is not None or self.random_metadata is not None:
                raise ValueError("P2 records must not contain P3 metadata")
        elif self.perturbation_type == "P3":
            if self.blosum62_score is not None:
                raise ValueError("P3 records must not contain blosum62_score")
            if self.random_seed is None or self.random_metadata is None:
                raise ValueError("P3 records require random_seed and random_metadata")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "PerturbationRecord":
        """Build a record from CSV-like values while enforcing exact fields."""

        supplied = set(values)
        required = set(PERTURBATION_FIELDS)
        missing = required - supplied
        unknown = supplied - required
        if missing:
            raise ValueError(f"Missing perturbation field(s): {sorted(missing)}")
        if unknown:
            raise ValueError(f"Unknown perturbation field(s): {sorted(unknown)}")

        normalized = dict(values)
        normalized["position"] = _parse_required_integer(values["position"], "position")
        normalized["blosum62_score"] = _parse_optional_integer(
            values["blosum62_score"],
            "blosum62_score",
        )
        normalized["random_seed"] = _parse_optional_integer(
            values["random_seed"],
            "random_seed",
        )
        for field in (
            "schema_version",
            "variant_id",
            "sequence_id",
            "original_sequence",
            "original_residue",
            "substituted_residue",
            "perturbed_sequence",
            "perturbation_type",
        ):
            normalized[field] = str(values[field])
        normalized["random_metadata"] = (
            None if values["random_metadata"] in (None, "") else str(values["random_metadata"])
        )
        return cls(**normalized)

    def as_dict(self) -> dict[str, str | int]:
        """Serialize in the frozen field order using blanks for non-applicable values."""

        return {
            "schema_version": self.schema_version,
            "variant_id": self.variant_id,
            "sequence_id": self.sequence_id,
            "original_sequence": self.original_sequence,
            "position": self.position,
            "original_residue": self.original_residue,
            "substituted_residue": self.substituted_residue,
            "perturbed_sequence": self.perturbed_sequence,
            "perturbation_type": self.perturbation_type,
            "blosum62_score": "" if self.blosum62_score is None else self.blosum62_score,
            "random_seed": "" if self.random_seed is None else self.random_seed,
            "random_metadata": self.random_metadata or "",
        }


def schema_definition() -> dict[str, Any]:
    """Return the canonical, machine-readable Task 3.10 schema document."""

    field_types = {
        "schema_version": ("string", False),
        "variant_id": ("string", False),
        "sequence_id": ("string", False),
        "original_sequence": ("string", False),
        "position": ("integer", False),
        "original_residue": ("amino_acid", False),
        "substituted_residue": ("amino_acid", False),
        "perturbed_sequence": ("string", False),
        "perturbation_type": ("enum:P1|P2|P3", False),
        "blosum62_score": ("integer", True),
        "random_seed": ("integer", True),
        "random_metadata": ("json_object", True),
    }
    return {
        "schema_name": "c3_aop_bcs_perturbation_record",
        "schema_version": PERTURBATION_SCHEMA_VERSION,
        "record_semantics": "one record represents exactly one one-position substitution",
        "fields": [
            {"name": name, "type": field_types[name][0], "nullable": field_types[name][1]}
            for name in PERTURBATION_FIELDS
        ],
        "position_index_base": 1,
        "standard_amino_acids": "".join(sorted(STANDARD_AMINO_ACIDS)),
        "perturbation_types": {
            "P1": "alanine scan at a redox residue",
            "P2": "BLOSUM62-conservative substitution at a non-redox residue",
            "P3": "seeded random single-residue substitution control",
        },
        "conditional_metadata": {
            "P1": {
                "blosum62_score": "must_be_null",
                "random_seed": "must_be_null",
                "random_metadata": "must_be_null",
            },
            "P2": {
                "blosum62_score": "required",
                "random_seed": "must_be_null",
                "random_metadata": "must_be_null",
            },
            "P3": {
                "blosum62_score": "must_be_null",
                "random_seed": "required",
                "random_metadata": "required_json_object",
            },
        },
        "invariants": [
            "original_sequence and perturbed_sequence have equal non-zero length",
            "position is one-based and within original_sequence",
            "original_residue matches original_sequence at position",
            "substituted_residue matches perturbed_sequence at position",
            "original_residue and substituted_residue differ",
            "original_sequence and perturbed_sequence differ only at position",
        ],
    }


def write_schema_document(path: str | Path = DEFAULT_SCHEMA_PATH) -> Path:
    """Write the canonical schema document with deterministic formatting."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema_definition(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_path


def main() -> None:
    output_path = write_schema_document()
    print(f"Wrote perturbation schema {PERTURBATION_SCHEMA_VERSION} to {output_path}")


if __name__ == "__main__":
    main()
