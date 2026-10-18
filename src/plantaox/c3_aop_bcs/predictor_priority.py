"""Validated PP1 predictor prioritization and PU-AOP handoff plan for Task 3.21."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .predictor_access import (
    DEFAULT_ACCESS_REGISTRY_PATH,
    EXPECTED_PREDICTOR_IDS,
    load_predictor_access_registry,
)


PREDICTOR_PRIORITY_SCHEMA_VERSION = "1.0"
PRIMARY_PREDICTORS = frozenset({"anoxpepred", "aopxsvm", "pu_aop"})
SECONDARY_PREDICTORS = frozenset({"multi_aop", "aop_drl"})
DEFAULT_PRIORITY_PLAN_PATH = Path(__file__).with_name("predictor_priority_v1.json")
DEFAULT_PRIORITY_REPORT_PATH = Path(__file__).parent / "docs" / "predictor_priority_scope.md"
DEFAULT_PU_AOP_HANDOFF_PATH = Path(__file__).parent / "docs" / "pu_aop_handoff_request.md"


class PredictorPriorityPlanError(ValueError):
    """Raised when the PP1 predictor-priority plan is incomplete or inconsistent."""


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PredictorPriorityPlanError(f"{field} must be a non-empty string")
    return value


def validate_predictor_priority_plan(
    plan: object,
    access_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate scope, ranking, handoff gates, and access-registry consistency."""

    if not isinstance(plan, dict):
        raise PredictorPriorityPlanError("priority plan must be a JSON object")
    if plan.get("schema_version") != PREDICTOR_PRIORITY_SCHEMA_VERSION:
        raise PredictorPriorityPlanError("unexpected predictor-priority schema version")
    _require_text(plan.get("decided_on"), "decided_on")

    access = access_registry or load_predictor_access_registry(DEFAULT_ACCESS_REGISTRY_PATH)
    access_by_id = {row["predictor_id"]: row for row in access["predictors"]}

    priorities = plan.get("priorities")
    if not isinstance(priorities, list):
        raise PredictorPriorityPlanError("priorities must be a list")
    ids = tuple(row.get("predictor_id") for row in priorities if isinstance(row, dict))
    if set(ids) != set(EXPECTED_PREDICTOR_IDS) or len(ids) != len(EXPECTED_PREDICTOR_IDS):
        raise PredictorPriorityPlanError("priorities must contain each required predictor exactly once")
    if sorted(row.get("integration_order") for row in priorities) != [1, 2, 3, 4, 5]:
        raise PredictorPriorityPlanError("integration_order must be the unique values 1 through 5")

    primary = {row["predictor_id"] for row in priorities if row.get("tier") == "primary"}
    secondary = {row["predictor_id"] for row in priorities if row.get("tier") == "secondary"}
    if primary != PRIMARY_PREDICTORS:
        raise PredictorPriorityPlanError(f"primary predictors must be {sorted(PRIMARY_PREDICTORS)}")
    if secondary != SECONDARY_PREDICTORS:
        raise PredictorPriorityPlanError(
            f"secondary predictors must be {sorted(SECONDARY_PREDICTORS)}"
        )

    for row in priorities:
        predictor_id = row["predictor_id"]
        _require_text(row.get("display_name"), f"{predictor_id}.display_name")
        _require_text(row.get("readiness"), f"{predictor_id}.readiness")
        _require_text(row.get("rationale"), f"{predictor_id}.rationale")
        if not isinstance(row.get("next_actions"), list) or not row["next_actions"]:
            raise PredictorPriorityPlanError(f"{predictor_id}.next_actions must not be empty")
        if row.get("integration_status") != access_by_id[predictor_id]["integration"]["status"]:
            raise PredictorPriorityPlanError(
                f"{predictor_id} integration status disagrees with Task 3.20 registry"
            )

    policy = plan.get("pp1_scope_policy")
    if not isinstance(policy, dict):
        raise PredictorPriorityPlanError("pp1_scope_policy must be an object")
    if set(policy.get("primary_predictors", [])) != PRIMARY_PREDICTORS:
        raise PredictorPriorityPlanError("scope policy has the wrong primary predictor set")
    if set(policy.get("secondary_predictors", [])) != SECONDARY_PREDICTORS:
        raise PredictorPriorityPlanError("scope policy has the wrong secondary predictor set")
    if policy.get("dummy_counts_as_real_predictor") is not False:
        raise PredictorPriorityPlanError("dummy predictor must never count as a real predictor")

    handoff = plan.get("pu_aop_handoff")
    if not isinstance(handoff, dict) or handoff.get("predictor_id") != "pu_aop":
        raise PredictorPriorityPlanError("PU-AOP handoff section is required")
    requirements = handoff.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise PredictorPriorityPlanError("PU-AOP handoff requirements must not be empty")
    requirement_ids = [item.get("requirement_id") for item in requirements]
    if len(requirement_ids) != len(set(requirement_ids)):
        raise PredictorPriorityPlanError("PU-AOP handoff requirement identifiers must be unique")
    if handoff.get("ready_for_c3_integration") is True:
        unverified = [
            item["requirement_id"]
            for item in requirements
            if item.get("required") is True and item.get("status") != "verified_for_handoff"
        ]
        if unverified:
            raise PredictorPriorityPlanError(
                "PU-AOP cannot be ready while required handoff items remain unverified"
            )

    issues = plan.get("unresolved_access_issues")
    if not isinstance(issues, list) or not issues:
        raise PredictorPriorityPlanError("unresolved_access_issues must not be empty")
    issue_ids = [issue.get("issue_id") for issue in issues]
    if len(issue_ids) != len(set(issue_ids)):
        raise PredictorPriorityPlanError("unresolved issue identifiers must be unique")
    for issue in issues:
        if issue.get("predictor_id") not in EXPECTED_PREDICTOR_IDS:
            raise PredictorPriorityPlanError("unresolved issue names an unknown predictor")
        _require_text(issue.get("exit_criterion"), f"{issue.get('issue_id')}.exit_criterion")
    return plan


def load_predictor_priority_plan(
    path: str | Path = DEFAULT_PRIORITY_PLAN_PATH,
) -> dict[str, Any]:
    """Load and validate the versioned PP1 predictor-priority plan."""

    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_predictor_priority_plan(plan)


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_predictor_priority_report(plan: dict[str, Any]) -> str:
    """Render the priority decision and unresolved issues as Markdown."""

    validate_predictor_priority_plan(plan)
    policy = plan["pp1_scope_policy"]
    lines = [
        "# PP1 Predictor Integration Scope (Task 3.21)",
        "",
        f"**Decision version:** `{plan['schema_version']}`  ",
        f"**Decision date:** `{plan['decided_on']}`  ",
        f"**PP1 floor:** {policy['demonstration_floor']}  ",
        f"**PP1 comparison target:** {policy['comparison_target']}",
        "",
        "| Order | Predictor | Tier | Readiness | Current integration | Rationale |",
        "|---:|---|---|---|---|---|",
    ]
    for row in sorted(plan["priorities"], key=lambda item: item["integration_order"]):
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    row["integration_order"],
                    row["display_name"],
                    row["tier"],
                    row["readiness"],
                    row["integration_status"],
                    row["rationale"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Scope rules",
            "",
            f"- {policy['single_predictor_label']}",
            f"- {policy['secondary_activation_rule']}",
            f"- {policy['integration_evidence_rule']}",
            "- The Task 3.22 dummy predictor is software-test-only and cannot satisfy the real-predictor floor.",
            "",
            "## Unresolved access issues",
            "",
            "| Issue | Predictor | Severity | Status | Exit criterion |",
            "|---|---|---|---|---|",
        ]
    )
    display_names = {row["predictor_id"]: row["display_name"] for row in plan["priorities"]}
    for issue in plan["unresolved_access_issues"]:
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    issue["issue_id"],
                    display_names[issue["predictor_id"]],
                    issue["severity"],
                    issue["status"],
                    issue["exit_criterion"],
                )
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def render_pu_aop_handoff_request(plan: dict[str, Any]) -> str:
    """Render the actionable Component 2 to Component 3 handoff checklist."""

    validate_predictor_priority_plan(plan)
    handoff = plan["pu_aop_handoff"]
    lines = [
        "# PU-AOP Frozen-Model Handoff Request",
        "",
        f"**From:** {handoff['requesting_component']}  ",
        f"**To:** {handoff['providing_component']}  ",
        f"**Status:** `{handoff['status']}`  ",
        f"**Ready for C3 integration:** `{str(handoff['ready_for_c3_integration']).lower()}`",
        "",
        "This checklist coordinates the frozen-model handoff without implying that PU-AOP is integrated. Component 3 will change that status only after every required item is verified and a retained reference sequence produces the supplied score through the C3 interface.",
        "",
        "| Requirement | Required | Current status | Evidence/expected content |",
        "|---|---|---|---|",
    ]
    for item in handoff["requirements"]:
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    item["requirement_id"],
                    str(item["required"]).lower(),
                    item["status"],
                    item["evidence_or_request"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Acceptance gate",
            "",
            f"- {handoff['acceptance_gate']}",
            f"- Scientific limitation to preserve: {handoff['scientific_limitation']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_priority_documents(
    plan_path: str | Path = DEFAULT_PRIORITY_PLAN_PATH,
    report_path: str | Path = DEFAULT_PRIORITY_REPORT_PATH,
    handoff_path: str | Path = DEFAULT_PU_AOP_HANDOFF_PATH,
) -> tuple[Path, Path]:
    """Write deterministic Markdown views of the versioned priority plan."""

    plan = load_predictor_priority_plan(plan_path)
    report = Path(report_path)
    handoff = Path(handoff_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    handoff.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_predictor_priority_report(plan), encoding="utf-8", newline="\n")
    handoff.write_text(render_pu_aop_handoff_request(plan), encoding="utf-8", newline="\n")
    return report, handoff


def main() -> None:
    report, handoff = write_priority_documents()
    print(f"Wrote {report} and {handoff}")


if __name__ == "__main__":
    main()
