"""Validated predictor-access registry and table renderer for Task 3.20."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PREDICTOR_ACCESS_SCHEMA_VERSION = "1.0"
EXPECTED_PREDICTOR_IDS = (
    "anoxpepred",
    "multi_aop",
    "aopxsvm",
    "aop_drl",
    "pu_aop",
)
DEFAULT_ACCESS_REGISTRY_PATH = Path(__file__).with_name("predictor_access_status_v1.json")
DEFAULT_ACCESS_TABLE_PATH = Path(__file__).parent / "docs" / "predictor_access_status.md"


class PredictorAccessRegistryError(ValueError):
    """Raised when the predictor-access registry violates its frozen contract."""


def _require_non_empty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PredictorAccessRegistryError(f"{field} must be a non-empty string")
    return value


def validate_predictor_access_registry(registry: object) -> dict[str, Any]:
    """Validate completeness and the no-unverified-integration policy."""

    if not isinstance(registry, dict):
        raise PredictorAccessRegistryError("registry must be a JSON object")
    if registry.get("schema_version") != PREDICTOR_ACCESS_SCHEMA_VERSION:
        raise PredictorAccessRegistryError("unexpected predictor-access schema version")
    _require_non_empty_string(registry.get("checked_on"), "checked_on")
    _require_non_empty_string(registry.get("integration_policy"), "integration_policy")

    predictors = registry.get("predictors")
    if not isinstance(predictors, list):
        raise PredictorAccessRegistryError("predictors must be a list")
    predictor_ids = tuple(
        predictor.get("predictor_id") if isinstance(predictor, dict) else None
        for predictor in predictors
    )
    if predictor_ids != EXPECTED_PREDICTOR_IDS:
        raise PredictorAccessRegistryError(
            f"predictors must appear exactly as {EXPECTED_PREDICTOR_IDS}"
        )

    for predictor in predictors:
        predictor_id = predictor["predictor_id"]
        _require_non_empty_string(predictor.get("display_name"), f"{predictor_id}.display_name")
        for section in (
            "code_model_availability",
            "expected_input",
            "output",
            "batch_scoring",
            "license_access",
            "integration",
        ):
            if not isinstance(predictor.get(section), dict):
                raise PredictorAccessRegistryError(f"{predictor_id}.{section} must be an object")

        batch = predictor["batch_scoring"]
        if not isinstance(batch.get("possible"), bool):
            raise PredictorAccessRegistryError(
                f"{predictor_id}.batch_scoring.possible must be boolean"
            )
        integration = predictor["integration"]
        verified = integration.get("real_score_verified")
        if not isinstance(verified, bool):
            raise PredictorAccessRegistryError(
                f"{predictor_id}.integration.real_score_verified must be boolean"
            )
        status = _require_non_empty_string(
            integration.get("status"), f"{predictor_id}.integration.status"
        )
        evidence = integration.get("score_evidence")
        if status == "integrated" and (not verified or not evidence):
            raise PredictorAccessRegistryError(
                f"{predictor_id} cannot be integrated without real score evidence"
            )
        if verified and not evidence:
            raise PredictorAccessRegistryError(
                f"{predictor_id} marks a score verified without score evidence"
            )

        sources = predictor.get("sources")
        if not isinstance(sources, list) or not sources:
            raise PredictorAccessRegistryError(f"{predictor_id}.sources must not be empty")
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                raise PredictorAccessRegistryError(
                    f"{predictor_id}.sources[{index}] must be an object"
                )
            _require_non_empty_string(
                source.get("label"), f"{predictor_id}.sources[{index}].label"
            )
            _require_non_empty_string(
                source.get("location"), f"{predictor_id}.sources[{index}].location"
            )
    return registry


def load_predictor_access_registry(
    path: str | Path = DEFAULT_ACCESS_REGISTRY_PATH,
) -> dict[str, Any]:
    """Load and validate the versioned predictor-access registry."""

    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_predictor_access_registry(registry)


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_predictor_access_table(registry: dict[str, Any]) -> str:
    """Render the reviewed access facts as a compact Markdown status table."""

    validate_predictor_access_registry(registry)
    lines = [
        "# Predictor Access Status (Task 3.20)",
        "",
        f"**Schema:** `{registry['schema_version']}`  ",
        f"**Checked:** `{registry['checked_on']}`  ",
        "**Integration rule:** A predictor remains `not_integrated` until a real score has been produced through the C3 predictor interface and retained as evidence.",
        "",
        "| Predictor | Code/model availability | Expected input | Output | Batch scoring | License/access limitations | C3 integration |",
        "|---|---|---|---|---|---|---|",
    ]
    for predictor in registry["predictors"]:
        integration = predictor["integration"]
        integration_summary = (
            f"`{integration['status']}`; real score verified: "
            f"`{str(integration['real_score_verified']).lower()}`. "
            f"{integration['summary']}"
        )
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    predictor["display_name"],
                    predictor["code_model_availability"]["summary"],
                    predictor["expected_input"]["summary"],
                    predictor["output"]["summary"],
                    predictor["batch_scoring"]["summary"],
                    predictor["license_access"]["summary"],
                    integration_summary,
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Evidence notes",
            "",
            "- Public repository availability does not prove that its environment reproduces or that C3 can score with it.",
            "- A reachable submission page does not prove an automatable API or a verified result.",
            "- Repository license status refers to the inspected repository files, not the publication's copyright licence.",
            "- PU-AOP upstream reports and source code are present, but the accepted ignored checkpoints/cache and their documented external backup are absent from this checkout.",
            "- The machine-readable registry contains the inspected revisions, URLs, local evidence paths, observations, and blockers.",
            "",
        ]
    )
    return "\n".join(lines)


def write_predictor_access_table(
    registry_path: str | Path = DEFAULT_ACCESS_REGISTRY_PATH,
    output_path: str | Path = DEFAULT_ACCESS_TABLE_PATH,
) -> Path:
    """Write a deterministic Markdown view of the access registry."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_predictor_access_table(load_predictor_access_registry(registry_path)),
        encoding="utf-8",
        newline="\n",
    )
    return output


def main() -> None:
    output = write_predictor_access_table()
    print(f"Wrote predictor access table to {output}")


if __name__ == "__main__":
    main()
