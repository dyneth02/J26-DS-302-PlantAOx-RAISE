"""Typed loader for the Component 3 AOP-BCS research configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import tomllib


DEFAULT_CONFIG_PATH = Path(__file__).with_name("research_config.toml")
STANDARD_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")
_CONFIG_FIELDS = frozenset(
    {
        "random_seed",
        "sequence_min_length",
        "sequence_max_length",
        "redox_residues",
        "cd_hit_identity_threshold",
        "primary_delta",
        "sensitivity_deltas",
        "pilot_dataset_size",
    }
)


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class ResearchConfig:
    """Validated constants controlling reproducible AOP-BCS experiments."""

    random_seed: int
    sequence_min_length: int
    sequence_max_length: int
    redox_residues: tuple[str, ...]
    cd_hit_identity_threshold: float
    primary_delta: float
    sensitivity_deltas: tuple[float, ...]
    pilot_dataset_size: int

    def __post_init__(self) -> None:
        if not _is_plain_int(self.random_seed) or not 0 <= self.random_seed <= 2**32 - 1:
            raise ValueError("random_seed must be an integer in the unsigned 32-bit range")

        if not _is_plain_int(self.sequence_min_length) or self.sequence_min_length <= 0:
            raise ValueError("sequence_min_length must be a positive integer")
        if not _is_plain_int(self.sequence_max_length) or self.sequence_max_length <= 0:
            raise ValueError("sequence_max_length must be a positive integer")
        if self.sequence_min_length > self.sequence_max_length:
            raise ValueError("sequence_min_length must not exceed sequence_max_length")

        if not self.redox_residues:
            raise ValueError("redox_residues must not be empty")
        if len(set(self.redox_residues)) != len(self.redox_residues):
            raise ValueError("redox_residues must not contain duplicates")
        invalid_residues = [
            residue
            for residue in self.redox_residues
            if not isinstance(residue, str)
            or len(residue) != 1
            or residue not in STANDARD_AMINO_ACIDS
        ]
        if invalid_residues:
            raise ValueError(
                "redox_residues must contain unique uppercase standard amino-acid symbols; "
                f"invalid values: {invalid_residues!r}"
            )

        if not isinstance(self.cd_hit_identity_threshold, (int, float)) or isinstance(
            self.cd_hit_identity_threshold, bool
        ) or not 0.0 < self.cd_hit_identity_threshold <= 1.0:
            raise ValueError("cd_hit_identity_threshold must be numeric and in (0, 1]")

        if not isinstance(self.primary_delta, (int, float)) or isinstance(
            self.primary_delta, bool
        ) or not 0.0 < self.primary_delta < 1.0:
            raise ValueError("primary_delta must be numeric and in (0, 1)")
        if not self.sensitivity_deltas:
            raise ValueError("sensitivity_deltas must not be empty")
        if any(
            not isinstance(delta, (int, float))
            or isinstance(delta, bool)
            or not 0.0 < delta < 1.0
            for delta in self.sensitivity_deltas
        ):
            raise ValueError("sensitivity_deltas must contain only numeric values in (0, 1)")
        if len(set(self.sensitivity_deltas)) != len(self.sensitivity_deltas):
            raise ValueError("sensitivity_deltas must not contain duplicates")
        if tuple(sorted(self.sensitivity_deltas)) != self.sensitivity_deltas:
            raise ValueError("sensitivity_deltas must be in ascending order")
        if self.primary_delta not in self.sensitivity_deltas:
            raise ValueError("primary_delta must be included in sensitivity_deltas")

        if not _is_plain_int(self.pilot_dataset_size) or self.pilot_dataset_size <= 0:
            raise ValueError("pilot_dataset_size must be a positive integer")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "ResearchConfig":
        """Construct a validated configuration from a TOML-compatible mapping."""

        supplied_fields = set(values)
        missing = _CONFIG_FIELDS - supplied_fields
        if missing:
            raise ValueError(f"Missing research configuration field(s): {sorted(missing)}")
        unknown = supplied_fields - _CONFIG_FIELDS
        if unknown:
            raise ValueError(f"Unknown research configuration field(s): {sorted(unknown)}")

        normalized = dict(values)
        if not isinstance(normalized["redox_residues"], (list, tuple)):
            raise ValueError("redox_residues must be an array")
        if not isinstance(normalized["sensitivity_deltas"], (list, tuple)):
            raise ValueError("sensitivity_deltas must be an array")
        normalized["redox_residues"] = tuple(normalized["redox_residues"])
        normalized["sensitivity_deltas"] = tuple(normalized["sensitivity_deltas"])
        return cls(**normalized)


def load_research_config(path: str | Path | None = None) -> ResearchConfig:
    """Load and validate the default or explicitly supplied C3 TOML configuration."""

    config_path = DEFAULT_CONFIG_PATH if path is None else Path(path)
    try:
        with config_path.open("rb") as config_file:
            document = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Could not load C3 research configuration from {config_path}: {exc}") from exc

    research = document.get("research")
    if not isinstance(research, dict):
        raise ValueError("C3 research configuration must contain a [research] table")
    return ResearchConfig.from_mapping(research)
