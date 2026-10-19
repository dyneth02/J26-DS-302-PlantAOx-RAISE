"""Fixed, pointwise score normalization for Task 3.24."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Iterable


NORMALIZATION_SCHEMA_VERSION = "c3_aop_bcs_score_normalization_v1"
DEFAULT_NORMALIZATION_PATH = Path(__file__).with_name("score_normalization_v1.json")
DEFAULT_NORMALIZATION_REPORT_PATH = Path(__file__).parent / "docs" / "score_normalization.md"
ALLOWED_MAPPINGS = {"identity_0_1", "clip_0_1"}
EXPECTED_REAL_PREDICTORS = {
    "anoxpepred",
    "multi_aop",
    "aopxsvm",
    "aop_drl",
    "pu_aop",
}


class ScoreNormalizationError(ValueError):
    """Raised when a normalization contract or native score is invalid."""


@dataclass(frozen=True, slots=True)
class NormalizedScore:
    """A retained native score and its fixed usable representation."""

    score_id: str
    mapping: str
    native_score: float
    usable_score: float
    transformed: bool


def load_normalization_registry(
    path: str | Path = DEFAULT_NORMALIZATION_PATH,
) -> dict[str, Any]:
    """Load and validate the versioned normalization registry."""

    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_normalization_registry(registry)


def validate_normalization_registry(registry: object) -> dict[str, Any]:
    """Validate completeness and the fixed pointwise-mapping policy."""

    if not isinstance(registry, dict):
        raise ScoreNormalizationError("normalization registry must be an object")
    if registry.get("schema_version") != NORMALIZATION_SCHEMA_VERSION:
        raise ScoreNormalizationError("unexpected normalization schema version")
    policy = registry.get("global_policy")
    if not isinstance(policy, dict):
        raise ScoreNormalizationError("global_policy must be an object")
    if policy.get("usable_range") != [0.0, 1.0]:
        raise ScoreNormalizationError("global usable range must be [0,1]")
    if policy.get("batch_wise_min_max_scaling") != "prohibited":
        raise ScoreNormalizationError("batch-wise min-max scaling must be prohibited")

    contracts = registry.get("score_contracts")
    if not isinstance(contracts, list) or not contracts:
        raise ScoreNormalizationError("score_contracts must be a non-empty list")
    score_ids = [contract.get("score_id") for contract in contracts]
    if any(not isinstance(score_id, str) or not score_id for score_id in score_ids):
        raise ScoreNormalizationError("every score contract needs a score_id")
    if len(score_ids) != len(set(score_ids)):
        raise ScoreNormalizationError("score_id values must be unique")

    predictor_ids = {contract.get("predictor_id") for contract in contracts}
    if not EXPECTED_REAL_PREDICTORS.issubset(predictor_ids):
        raise ScoreNormalizationError("all five real predictor families must be covered")

    for contract in contracts:
        score_id = contract["score_id"]
        if contract.get("mapping") not in ALLOWED_MAPPINGS:
            raise ScoreNormalizationError(f"{score_id} uses an unsupported mapping")
        if contract.get("usable_range") != [0.0, 1.0]:
            raise ScoreNormalizationError(f"{score_id} must map to [0,1]")
        native_range = contract.get("native_range")
        if not isinstance(native_range, dict):
            raise ScoreNormalizationError(f"{score_id}.native_range must be an object")
        lower = native_range.get("lower")
        upper = native_range.get("upper")
        if isinstance(lower, bool) or not isinstance(lower, Real):
            raise ScoreNormalizationError(f"{score_id} needs a numeric native lower bound")
        if upper is not None and (isinstance(upper, bool) or not isinstance(upper, Real)):
            raise ScoreNormalizationError(f"{score_id} native upper bound must be numeric or null")
        if upper is not None and float(lower) > float(upper):
            raise ScoreNormalizationError(f"{score_id} native bounds are reversed")
        if contract["mapping"] == "identity_0_1" and (
            float(lower) != 0.0 or upper is None or float(upper) != 1.0
        ):
            raise ScoreNormalizationError(f"{score_id} identity mapping requires native [0,1]")
        if contract["mapping"] == "clip_0_1" and contract.get("preserves_native_value"):
            raise ScoreNormalizationError(f"{score_id} clipping cannot claim to preserve all values")
        if contract.get("operational_status") != "verified_software_smoke_only" and contract.get(
            "experimental_allowed"
        ):
            raise ScoreNormalizationError(
                f"{score_id} cannot allow experiments before real-score verification"
            )

    return registry


def _contract(registry: dict[str, Any], score_id: str) -> dict[str, Any]:
    for contract in registry["score_contracts"]:
        if contract["score_id"] == score_id:
            return contract
    raise ScoreNormalizationError(f"unknown score_id {score_id!r}")


def normalize_score(
    native_score: object,
    score_id: str,
    registry: dict[str, Any] | None = None,
) -> NormalizedScore:
    """Apply one fixed mapping without using any batch statistics."""

    active_registry = registry or load_normalization_registry()
    validate_normalization_registry(active_registry)
    contract = _contract(active_registry, score_id)
    if isinstance(native_score, bool) or not isinstance(native_score, Real):
        raise ScoreNormalizationError(f"{score_id} native score must be numeric")
    native = float(native_score)
    if not math.isfinite(native):
        raise ScoreNormalizationError(f"{score_id} native score must be finite")

    lower = float(contract["native_range"]["lower"])
    upper_value = contract["native_range"]["upper"]
    upper = None if upper_value is None else float(upper_value)
    if native < lower or (upper is not None and native > upper):
        raise ScoreNormalizationError(
            f"{score_id} native score {native!r} is outside its declared range"
        )

    mapping = contract["mapping"]
    usable = native if mapping == "identity_0_1" else min(1.0, max(0.0, native))
    if not 0.0 <= usable <= 1.0:
        raise ScoreNormalizationError(f"{score_id} usable score is outside [0,1]")
    return NormalizedScore(
        score_id=score_id,
        mapping=mapping,
        native_score=native,
        usable_score=usable,
        transformed=usable != native,
    )


def normalize_scores(
    native_scores: Iterable[object],
    score_id: str,
    registry: dict[str, Any] | None = None,
) -> list[NormalizedScore]:
    """Normalize independently; collection membership cannot affect a result."""

    active_registry = registry or load_normalization_registry()
    return [normalize_score(value, score_id, active_registry) for value in native_scores]


def render_normalization_report(registry: dict[str, Any]) -> str:
    """Render the frozen registry as a concise human-readable contract."""

    validate_normalization_registry(registry)
    lines = [
        "# Score Normalization Contract (Task 3.24)",
        "",
        f"**Schema:** `{registry['schema_version']}`  ",
        f"**Created:** `{registry['created_on']}`  ",
        "**Usable score range:** `[0,1]` with higher values meaning stronger AOP support.",
        "",
        "Native scores are always retained. Every mapping is fixed and pointwise: the same native value produces the same usable value regardless of batch composition. Batch-wise min-max scaling is prohibited.",
        "",
        "| Score contract | Native range | Mapping | Native retained unchanged | Status | Experimental use |",
        "|---|---:|---|---:|---|---:|",
    ]
    for contract in registry["score_contracts"]:
        native = contract["native_range"]
        upper = "unbounded" if native["upper"] is None else str(native["upper"])
        native_range = f"[{native['lower']}, {upper}]"
        lines.append(
            f"| {contract['display_name']} (`{contract['score_id']}`) | {native_range} | "
            f"`{contract['mapping']}` | {str(contract['preserves_native_value']).lower()} | "
            f"`{contract['operational_status']}` | "
            f"{str(contract['experimental_allowed']).lower()} |"
        )

    validation = registry["operational_validation"]
    lines.extend(
        [
            "",
            "## Operational validation",
            "",
            f"The current validation status is `{validation['status']}`. The full dummy smoke dataset supplied {validation['score_value_count']:,} original/perturbed score values across {validation['row_count']:,} perturbation rows. Its native and usable ranges were both `{validation['usable_min']}` to `{validation['usable_max']}`, with zero out-of-range or transformed values.",
            "",
            "This confirms the normalization software and `[0,1]` enforcement, not a scientific predictor. Every real predictor remains pending until a real C3 score is retained and checked against its contract.",
            "",
            "## Predictor-specific decisions",
            "",
            "- AnOxPePred's FRS and Chelator sigmoid channels remain separate; C3 must prespecify the scalar endpoint rather than silently averaging them.",
            "- Multi-AOP, AOPxSVM, AOP-DRL, PU-AOP M1-M3, and PU-AOP M5 use identity mappings when their documented `[0,1]` outputs are eventually verified.",
            "- PU-AOP M4 retains its raw Elkan-Noto corrected score and creates a separate fixed `clip(raw, 0, 1)` usable value. No batch-derived mapping is permitted.",
            "- The dummy mapping is verified for software testing only and remains prohibited from experimental results.",
            "",
        ]
    )
    return "\n".join(lines)


def write_normalization_report(
    output_path: str | Path = DEFAULT_NORMALIZATION_REPORT_PATH,
    registry_path: str | Path = DEFAULT_NORMALIZATION_PATH,
) -> Path:
    """Regenerate the deterministic Markdown report from the JSON contract."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_normalization_report(load_normalization_registry(registry_path)),
        encoding="utf-8",
        newline="\n",
    )
    return path


if __name__ == "__main__":
    write_normalization_report()
