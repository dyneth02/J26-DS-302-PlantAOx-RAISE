"""Validation and rendering for the C2 five-model handoff audit.

The audit is owned by Component 3. Component 2 artifacts are evidence inputs
only and are never modified by this module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACKAGE_DIRECTORY = Path(__file__).parent
DEFAULT_AUDIT_PATH = PACKAGE_DIRECTORY / "pu_aop_five_model_audit_v1.json"
DEFAULT_REPORT_PATH = PACKAGE_DIRECTORY / "docs" / "pu_aop_five_model_audit.md"
EXPECTED_MODEL_IDS = {"M1", "M2", "M3", "M4", "M5"}


class PuAopAuditError(ValueError):
    """Raised when the frozen audit record is incomplete or contradictory."""


def load_pu_aop_audit(path: Path = DEFAULT_AUDIT_PATH) -> dict[str, Any]:
    """Load and validate the machine-readable audit."""

    with path.open(encoding="utf-8") as handle:
        audit = json.load(handle)
    validate_pu_aop_audit(audit)
    return audit


def validate_pu_aop_audit(audit: dict[str, Any]) -> None:
    """Enforce the evidence and no-premature-integration boundaries."""

    if audit.get("schema_version") != "c3_pu_aop_five_model_audit_v1":
        raise PuAopAuditError("unexpected audit schema version")

    models = audit.get("models", [])
    model_ids = {model.get("model_id") for model in models}
    if len(models) != 5 or model_ids != EXPECTED_MODEL_IDS:
        raise PuAopAuditError("audit must cover exactly M1 through M5")

    for model in models:
        if model.get("checkpoint_available_in_current_checkout"):
            raise PuAopAuditError(
                f"{model['model_id']} cannot be recorded available without a new filesystem audit"
            )
        if model.get("c3_integration_status") != "not_integrated":
            raise PuAopAuditError(
                f"{model['model_id']} cannot be integrated without a reproduced reference score"
            )
        metrics = model.get("assay_supported_fold0", {})
        if metrics.get("n_positive") != 124 or metrics.get("n_inactive_control") != 38:
            raise PuAopAuditError(f"{model['model_id']} has unexpected evaluation membership")

    missing = audit.get("missing_or_unresolved", [])
    missing_ids = {item.get("id") for item in missing}
    if missing_ids != {f"C2-HANDOFF-{index:02d}" for index in range(1, 11)}:
        raise PuAopAuditError("audit must retain all ten identified handoff findings")
    if not any(item.get("severity") == "blocking" for item in missing):
        raise PuAopAuditError("audit must retain its blocking findings")

    if audit.get("integration_gate", {}).get("ready"):
        raise PuAopAuditError("integration gate cannot pass while checkpoints and fixtures are missing")


def render_pu_aop_audit_report(audit: dict[str, Any]) -> str:
    """Render the validated audit as a concise human-readable report."""

    validate_pu_aop_audit(audit)
    lines = [
        "# Component 2 PU-AOP Five-Model Audit",
        "",
        f"**Audit date:** {audit['audit_date']}",
        "",
        "**Scope:** Read-only inspection of Component 2; this report and its JSON evidence are owned by Component 3.",
        "",
        "**Decision:** Not ready for verified C3 scoring. Component 2 documents five technically accepted fold-0 configurations, but none is integrated in C3.",
        "",
        "## Model-by-model result",
        "",
        "| ID | Model | Native output | Checkpoint here | MCC | AUROC | C3 status |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for model in audit["models"]:
        metrics = model["assay_supported_fold0"]
        checkpoint = "yes" if model["checkpoint_available_in_current_checkout"] else "no"
        lines.append(
            f"| {model['model_id']} | {model['name']} | {model['native_score']} | "
            f"{checkpoint} | {metrics['mcc']:.3f} | {metrics['auroc']:.3f} | "
            f"{model['c3_integration_status']} |"
        )

    lines.extend(
        [
            "",
            "The metrics above use the common fold-0 assay-supported comparison of 124 held-out positives and 38 assay-inactive controls at threshold 0.5. All five MCC values are negative and all five AUROC values are below 0.5. This is a scientifically important limitation; technical acceptance is not evidence of reliable antioxidant discrimination.",
            "",
            "C1, C2, and C3 are unlabeled assumption pools. Any metrics that temporarily assign them a negative label are proxy diagnostics only and must not be described as confirmed-negative performance.",
            "",
            "## What is already documented",
            "",
            "- All models use fold 0 and the 495-dimensional `fusion_v1` representation.",
            "- Feature order is 480 mean-pooled ESM-2 values followed by the 15 frozen descriptors.",
            "- The ESM model is `esm2_t12_35M_UR50D`, layer 12; BOS, EOS, and padding are excluded from mean pooling.",
            "- Fold-0 scaler parameters and descriptor/fusion schemas are present and checksum-pinned.",
            "- Higher scores mean stronger support for the positive/AOP class; the evaluation threshold is 0.5.",
            "- M1-M3 return sigmoid outputs; M5 returns bounded class-1 `predict_proba` output.",
            "- M4 returns an Elkan-Noto-corrected raw score that can exceed 1; its clipped copy is used only for threshold and Brier calculations.",
            "",
            "## Missing or unresolved information",
            "",
        ]
    )
    for item in audit["missing_or_unresolved"]:
        models = ", ".join(item["applies_to"])
        lines.append(
            f"- **{item['id']} ({item['severity']}; {models}):** {item['missing']} "
            f"Required resolution: {item['needed']}"
        )

    lines.extend(
        [
            "",
            "## Artifact availability finding",
            "",
            "The freeze inventory says the checkpoint and cache artifacts were available locally in the freeze author's environment, but all five recorded checkpoint paths and `fr3_fold0_scaled_features.npz` are absent from this checkout. The documented backup path belongs to `C:/Users/metal/...` and does not exist on the current machine. The small descriptor-only prototype artifact is explicitly marked as prototype mode and is not a substitute for any accepted model.",
            "",
            "## PU-Bagging contradiction",
            "",
            "The accepted M5 run summary records `n_estimators=10` and `max_samples=1.0`. Component 2's implementation-status decision log and PP1 planner state `n_estimators=100`. Until Component 2 confirms which setting belongs to the frozen checkpoint, the run summary and checkpoint hash must be treated as the closest evidence, but M5 cannot pass the handoff gate.",
            "",
            "## Minimum handoff needed by C3",
            "",
        ]
    )
    for requirement in audit["integration_gate"]["requirements"]:
        lines.append(f"- {requirement}")

    lines.extend(
        [
            "",
            "After these conditions are met, C3 can wrap each approved configuration behind the Task 3.19 predictor interface, reproduce its reference score, and only then change its status from `not_integrated`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_pu_aop_audit_report(path: Path = DEFAULT_REPORT_PATH) -> Path:
    """Regenerate the Markdown report from the audited JSON record."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_pu_aop_audit_report(load_pu_aop_audit()), encoding="utf-8")
    return path


if __name__ == "__main__":
    write_pu_aop_audit_report()
