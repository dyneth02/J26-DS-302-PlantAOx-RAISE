"""Schema and dependency boundary for the later SHAP-faithfulness study."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from .config import STANDARD_AMINO_ACIDS, load_research_config
from .predictor_interface import Predictor


SHAP_FAITHFULNESS_SCHEMA_VERSION = "1.0"
SHAP_FAITHFULNESS_SCHEMA_ID = "c3_aop_bcs_shap_faithfulness_v1"
DEFAULT_SCHEMA_PATH = Path(__file__).with_name("shap_faithfulness_schema_v1.json")
DEFAULT_PLAN_PATH = Path(__file__).with_name("docs") / "shap_faithfulness_plan.md"

SHAP_FAITHFULNESS_FIELDS = (
    "schema_version",
    "sequence_id",
    "sequence",
    "predictor_id",
    "predictor_version",
    "residue_position",
    "residue",
    "p1_variant_id",
    "shap_value",
    "absolute_shap_value",
    "p1_delta_score",
    "absolute_p1_delta_score",
    "kernel_shap_backend",
    "kernel_shap_version",
    "background_dataset_version",
    "random_seed",
)


class ShapFaithfulnessError(ValueError):
    """Raised when SHAP-faithfulness metadata or joins violate the contract."""


def _trimmed(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ShapFaithfulnessError(f"{name} must be a non-empty trimmed string")
    return value


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ShapFaithfulnessError(f"{name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ShapFaithfulnessError(f"{name} must be finite")
    return normalized


def _parse_finite(value: object, name: str) -> float:
    if isinstance(value, str):
        try:
            return _finite(float(value), name)
        except ValueError as exc:
            raise ShapFaithfulnessError(f"{name} must be numeric") from exc
    return _finite(value, name)


def _float_text(value: float) -> str:
    return format(value, ".17g")


@dataclass(frozen=True, slots=True)
class KernelShapRequest:
    """Predictor-independent request passed to a future KernelSHAP backend."""

    sequence_id: str
    sequence: str
    predictor_id: str
    predictor_version: str
    background_dataset_version: str
    random_seed: int

    def __post_init__(self) -> None:
        for name in (
            "sequence_id",
            "predictor_id",
            "predictor_version",
            "background_dataset_version",
        ):
            _trimmed(getattr(self, name), name)
        if not isinstance(self.sequence, str) or not self.sequence:
            raise ShapFaithfulnessError("sequence must be a non-empty string")
        if self.sequence != self.sequence.upper() or set(self.sequence) - STANDARD_AMINO_ACIDS:
            raise ShapFaithfulnessError(
                "sequence must contain only uppercase standard amino-acid symbols"
            )
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise ShapFaithfulnessError("random_seed must be an integer")
        if not 0 <= self.random_seed <= 2**32 - 1:
            raise ShapFaithfulnessError("random_seed must be in the unsigned 32-bit range")


@dataclass(frozen=True, slots=True)
class KernelShapExplanation:
    """One validated per-residue explanation returned by a future backend."""

    values: tuple[float, ...]
    backend_id: str
    backend_version: str

    def __post_init__(self) -> None:
        _trimmed(self.backend_id, "backend_id")
        _trimmed(self.backend_version, "backend_version")
        if not isinstance(self.values, tuple) or not self.values:
            raise ShapFaithfulnessError("values must be a non-empty tuple")
        for index, value in enumerate(self.values, start=1):
            _finite(value, f"SHAP value at position {index}")


@runtime_checkable
class KernelShapBackend(Protocol):
    """Pluggable boundary; concrete SHAP execution is intentionally deferred."""

    @property
    def backend_id(self) -> str:
        """Return a stable backend identifier."""

    @property
    def version(self) -> str:
        """Return the backend implementation or dependency version."""

    def explain(
        self,
        request: KernelShapRequest,
        predictor: Predictor,
    ) -> KernelShapExplanation:
        """Return exactly one finite SHAP value per sequence position."""


@dataclass(frozen=True, slots=True)
class ShapFaithfulnessRecord:
    """One P1-linked residue observation for the later faithfulness analysis."""

    sequence_id: str
    sequence: str
    predictor_id: str
    predictor_version: str
    residue_position: int
    residue: str
    p1_variant_id: str
    shap_value: float
    absolute_shap_value: float
    p1_delta_score: float
    absolute_p1_delta_score: float
    kernel_shap_backend: str
    kernel_shap_version: str
    background_dataset_version: str
    random_seed: int
    schema_version: str = SHAP_FAITHFULNESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SHAP_FAITHFULNESS_SCHEMA_VERSION:
            raise ShapFaithfulnessError("unsupported SHAP-faithfulness schema version")
        for name in (
            "sequence_id",
            "predictor_id",
            "predictor_version",
            "p1_variant_id",
            "kernel_shap_backend",
            "kernel_shap_version",
            "background_dataset_version",
        ):
            _trimmed(getattr(self, name), name)
        if not isinstance(self.sequence, str) or not self.sequence:
            raise ShapFaithfulnessError("sequence must be a non-empty string")
        if self.sequence != self.sequence.upper() or set(self.sequence) - STANDARD_AMINO_ACIDS:
            raise ShapFaithfulnessError(
                "sequence must contain only uppercase standard amino-acid symbols"
            )
        if isinstance(self.residue_position, bool) or not isinstance(
            self.residue_position, int
        ):
            raise ShapFaithfulnessError("residue_position must be an integer")
        if not 1 <= self.residue_position <= len(self.sequence):
            raise ShapFaithfulnessError(
                "residue_position must use one-based indexing within sequence"
            )
        if self.residue != self.sequence[self.residue_position - 1]:
            raise ShapFaithfulnessError("residue does not match sequence at residue_position")
        if self.residue not in load_research_config().redox_residues:
            raise ShapFaithfulnessError("P1-linked residue must belong to the redox set")
        shap = _finite(self.shap_value, "shap_value")
        absolute_shap = _finite(self.absolute_shap_value, "absolute_shap_value")
        delta = _finite(self.p1_delta_score, "p1_delta_score")
        absolute_delta = _finite(
            self.absolute_p1_delta_score, "absolute_p1_delta_score"
        )
        if not math.isclose(absolute_shap, abs(shap), rel_tol=0.0, abs_tol=1e-12):
            raise ShapFaithfulnessError("absolute_shap_value must equal abs(shap_value)")
        if not math.isclose(absolute_delta, abs(delta), rel_tol=0.0, abs_tol=1e-12):
            raise ShapFaithfulnessError(
                "absolute_p1_delta_score must equal abs(p1_delta_score)"
            )
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise ShapFaithfulnessError("random_seed must be an integer")
        if not 0 <= self.random_seed <= 2**32 - 1:
            raise ShapFaithfulnessError("random_seed must be in the unsigned 32-bit range")

    @classmethod
    def create(
        cls,
        *,
        request: KernelShapRequest,
        explanation: KernelShapExplanation,
        residue_position: int,
        p1_variant_id: str,
        p1_delta_score: object,
    ) -> "ShapFaithfulnessRecord":
        """Create a record while deriving both absolute-value fields."""

        if len(explanation.values) != len(request.sequence):
            raise ShapFaithfulnessError(
                "KernelSHAP must return exactly one value per sequence position"
            )
        if not 1 <= residue_position <= len(request.sequence):
            raise ShapFaithfulnessError("residue_position is outside the request sequence")
        shap_value = _finite(
            explanation.values[residue_position - 1], "shap_value"
        )
        delta_value = _parse_finite(p1_delta_score, "p1_delta_score")
        return cls(
            sequence_id=request.sequence_id,
            sequence=request.sequence,
            predictor_id=request.predictor_id,
            predictor_version=request.predictor_version,
            residue_position=residue_position,
            residue=request.sequence[residue_position - 1],
            p1_variant_id=p1_variant_id,
            shap_value=shap_value,
            absolute_shap_value=abs(shap_value),
            p1_delta_score=delta_value,
            absolute_p1_delta_score=abs(delta_value),
            kernel_shap_backend=explanation.backend_id,
            kernel_shap_version=explanation.backend_version,
            background_dataset_version=request.background_dataset_version,
            random_seed=request.random_seed,
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "ShapFaithfulnessRecord":
        """Load and validate one record from a CSV-compatible mapping."""

        if set(values) != set(SHAP_FAITHFULNESS_FIELDS):
            raise ShapFaithfulnessError(
                "SHAP-faithfulness record fields do not match the frozen schema"
            )
        try:
            position = int(str(values["residue_position"]))
            seed = int(str(values["random_seed"]))
        except ValueError as exc:
            raise ShapFaithfulnessError(
                "residue_position and random_seed must be integers"
            ) from exc
        return cls(
            schema_version=str(values["schema_version"]),
            sequence_id=str(values["sequence_id"]),
            sequence=str(values["sequence"]),
            predictor_id=str(values["predictor_id"]),
            predictor_version=str(values["predictor_version"]),
            residue_position=position,
            residue=str(values["residue"]),
            p1_variant_id=str(values["p1_variant_id"]),
            shap_value=_parse_finite(values["shap_value"], "shap_value"),
            absolute_shap_value=_parse_finite(
                values["absolute_shap_value"], "absolute_shap_value"
            ),
            p1_delta_score=_parse_finite(
                values["p1_delta_score"], "p1_delta_score"
            ),
            absolute_p1_delta_score=_parse_finite(
                values["absolute_p1_delta_score"], "absolute_p1_delta_score"
            ),
            kernel_shap_backend=str(values["kernel_shap_backend"]),
            kernel_shap_version=str(values["kernel_shap_version"]),
            background_dataset_version=str(values["background_dataset_version"]),
            random_seed=seed,
        )

    def as_dict(self) -> dict[str, str]:
        """Return the frozen CSV representation."""

        return {
            "schema_version": self.schema_version,
            "sequence_id": self.sequence_id,
            "sequence": self.sequence,
            "predictor_id": self.predictor_id,
            "predictor_version": self.predictor_version,
            "residue_position": str(self.residue_position),
            "residue": self.residue,
            "p1_variant_id": self.p1_variant_id,
            "shap_value": _float_text(self.shap_value),
            "absolute_shap_value": _float_text(self.absolute_shap_value),
            "p1_delta_score": _float_text(self.p1_delta_score),
            "absolute_p1_delta_score": _float_text(self.absolute_p1_delta_score),
            "kernel_shap_backend": self.kernel_shap_backend,
            "kernel_shap_version": self.kernel_shap_version,
            "background_dataset_version": self.background_dataset_version,
            "random_seed": str(self.random_seed),
        }


def pair_kernel_shap_with_p1_deltas(
    request: KernelShapRequest,
    explanation: KernelShapExplanation,
    p1_delta_rows: Sequence[Mapping[str, object]],
) -> tuple[ShapFaithfulnessRecord, ...]:
    """Join one explanation to validated P1 DeltaScores at matching positions."""

    if len(explanation.values) != len(request.sequence):
        raise ShapFaithfulnessError(
            "KernelSHAP must return exactly one value per sequence position"
        )
    if not p1_delta_rows:
        raise ShapFaithfulnessError("at least one matching P1 DeltaScore is required")
    records: list[ShapFaithfulnessRecord] = []
    seen_positions: set[int] = set()
    for row in p1_delta_rows:
        if row.get("perturbation_type") != "P1":
            raise ShapFaithfulnessError("faithfulness comparison accepts only P1 rows")
        expected = {
            "sequence_id": request.sequence_id,
            "original_sequence": request.sequence,
            "predictor_id": request.predictor_id,
            "predictor_version": request.predictor_version,
            "substituted_residue": "A",
        }
        for field, expected_value in expected.items():
            if row.get(field) != expected_value:
                raise ShapFaithfulnessError(
                    f"P1 DeltaScore {field} does not match the KernelSHAP request"
                )
        try:
            position = int(str(row["position"]))
        except (KeyError, ValueError) as exc:
            raise ShapFaithfulnessError("P1 position must be an integer") from exc
        if position in seen_positions:
            raise ShapFaithfulnessError("duplicate P1 DeltaScore position")
        seen_positions.add(position)
        if not 1 <= position <= len(request.sequence):
            raise ShapFaithfulnessError("P1 position is outside the request sequence")
        if row.get("original_residue") != request.sequence[position - 1]:
            raise ShapFaithfulnessError("P1 original residue does not match sequence")
        delta = _parse_finite(row.get("delta_score"), "p1_delta_score")
        absolute_delta = _parse_finite(
            row.get("absolute_delta_score"), "absolute_p1_delta_score"
        )
        if not math.isclose(absolute_delta, abs(delta), rel_tol=0.0, abs_tol=1e-12):
            raise ShapFaithfulnessError("P1 absolute DeltaScore is inconsistent")
        records.append(
            ShapFaithfulnessRecord.create(
                request=request,
                explanation=explanation,
                residue_position=position,
                p1_variant_id=_trimmed(row.get("variant_id"), "p1_variant_id"),
                p1_delta_score=delta,
            )
        )
    return tuple(sorted(records, key=lambda record: record.residue_position))


def schema_document() -> dict[str, Any]:
    """Return the frozen Task 3.36 schema and later-analysis plan."""

    fields = {
        "schema_version": ("string", "fixed schema version"),
        "sequence_id": ("string", "stable peptide identifier"),
        "sequence": ("string", "uppercase original peptide sequence"),
        "predictor_id": ("string", "common-interface predictor identifier"),
        "predictor_version": ("string", "frozen predictor/model version"),
        "residue_position": ("integer", "one-based P1 residue position"),
        "residue": ("string", "original redox residue at residue_position"),
        "p1_variant_id": ("string", "linked alanine-scan variant identifier"),
        "shap_value": ("number", "signed per-residue KernelSHAP value"),
        "absolute_shap_value": ("number", "abs(shap_value)"),
        "p1_delta_score": ("number", "signed Score(original) - Score(P1 variant)"),
        "absolute_p1_delta_score": ("number", "abs(p1_delta_score)"),
        "kernel_shap_backend": ("string", "stable backend identifier"),
        "kernel_shap_version": ("string", "backend/dependency version"),
        "background_dataset_version": ("string", "frozen SHAP background version"),
        "random_seed": ("integer", "seed used by explanation procedure"),
    }
    return {
        "schema_version": SHAP_FAITHFULNESS_SCHEMA_VERSION,
        "schema_id": SHAP_FAITHFULNESS_SCHEMA_ID,
        "record_semantics": (
            "one record links one predictor's SHAP value at one redox residue "
            "to the matching P1 alanine-scan DeltaScore"
        ),
        "fields": [
            {"name": name, "type": fields[name][0], "description": fields[name][1]}
            for name in SHAP_FAITHFULNESS_FIELDS
        ],
        "primary_comparison": {
            "x": "absolute_shap_value",
            "y": "absolute_p1_delta_score",
            "notation": "|SHAP_i| vs |DeltaScore_i|",
            "planned_measure": "Pearson correlation r",
            "scope": "P1 redox-residue positions, evaluated per predictor",
            "interpretation": (
                "higher positive association supports attribution faithfulness; "
                "signed values remain stored for directional interpretation"
            ),
        },
        "kernel_shap_boundary": {
            "request_type": "KernelShapRequest",
            "backend_protocol": "KernelShapBackend",
            "result_type": "KernelShapExplanation",
            "required_output": "exactly one finite SHAP value per sequence position",
            "predictor_contract": "Task 3.19 Predictor interface",
            "concrete_backend_implemented": False,
            "shap_dependency_required_for_task_3_36": False,
        },
        "validation_rules": [
            "residue_position is one-based and within sequence",
            "residue matches sequence at residue_position and belongs to the redox set",
            "P1 row matches sequence, predictor, version, position, residue, and alanine replacement",
            "SHAP and DeltaScore values are finite",
            "absolute values equal the magnitudes of their signed values",
            "each sequence/predictor/P1 position occurs at most once",
        ],
        "pp1_scope": {
            "status": "SCHEMA_AND_MODULE_BOUNDARY_ONLY",
            "complete_shap_experiment_required_for_pp1": False,
            "scientific_shap_results_produced": False,
            "deferred_work": [
                "select and freeze a scientifically justified KernelSHAP background",
                "implement and verify a concrete KernelSHAP backend",
                "run real integrated predictors",
                "calculate and statistically interpret faithfulness correlations",
            ],
        },
    }


def render_implementation_plan(document: Mapping[str, Any]) -> str:
    """Render a concise human-readable plan from the schema contract."""

    field_rows = "\n".join(
        f"| `{field['name']}` | {field['type']} | {field['description']} |"
        for field in document["fields"]
    )
    deferred = "\n".join(
        f"- {item}" for item in document["pp1_scope"]["deferred_work"]
    )
    return f"""# SHAP-faithfulness preparation (Task 3.36)

**Schema:** `{document['schema_id']}`  
**PP1 scope:** schema and module boundary only; no SHAP experiment or scientific SHAP result is claimed.

## Record meaning

{document['record_semantics']}.

| Field | Type | Meaning |
|---|---|---|
{field_rows}

## Planned comparison

The later analysis compares `{document['primary_comparison']['notation']}` using {document['primary_comparison']['planned_measure']} at matched P1 redox-residue positions for each predictor. Signed SHAP and DeltaScore values remain available for directional interpretation.

## KernelSHAP boundary

`KernelShapRequest` carries sequence, predictor, background-version, and seed metadata. A future `KernelShapBackend` receives that request plus the Task 3.19 predictor interface and must return a `KernelShapExplanation` containing exactly one finite value per sequence position. `pair_kernel_shap_with_p1_deltas` performs the validated P1 join.

No concrete backend and no `shap` dependency are required for Task 3.36.

## Deferred after PP1 preparation

{deferred}
"""


def write_schema_and_plan(
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    plan_path: str | Path = DEFAULT_PLAN_PATH,
) -> tuple[Path, Path]:
    """Write deterministic machine-readable and human-readable artifacts."""

    document = schema_document()
    schema_output, plan_output = Path(schema_path), Path(plan_path)
    schema_output.parent.mkdir(parents=True, exist_ok=True)
    plan_output.parent.mkdir(parents=True, exist_ok=True)
    schema_output.write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    plan_output.write_text(
        render_implementation_plan(document), encoding="utf-8", newline="\n"
    )
    return schema_output, plan_output


if __name__ == "__main__":
    schema_file, plan_file = write_schema_and_plan()
    print(f"Wrote {schema_file} and {plan_file}")
