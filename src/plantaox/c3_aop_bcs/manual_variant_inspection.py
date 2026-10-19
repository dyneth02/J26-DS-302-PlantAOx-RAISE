"""Traceable PP1 example-variant inspection evidence for Task 3.33."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .blosum62 import load_blosum62, select_conservative_substitution
from .config import ResearchConfig, load_research_config
from .delta_score import (
    DELTA_SCORE_DATASET_VERSION,
    DELTA_SCORE_FIELDS,
    DEFAULT_OUTPUT_PATH as DEFAULT_INPUT_PATH,
)
from .dummy_predictor import DummySmokeTestPredictor
from .standardization import REPOSITORY_ROOT


INSPECTION_SCHEMA_VERSION = "1.0"
INSPECTION_VERSION = "c3_aop_bcs_pp1_manual_variant_inspection_v1"
REPRESENTATIVE_VARIANT_IDS = (
    "C3-ANOX-000205-P1-01-WA",
    "C3-ANOX-000467-P1-24-YA",
    "C3-MAOP-AOPP-001031-P2-01-LI",
    "C3-ANOX-000074-P2-06-VI",
    "C3-MAOP-ANOXPP-000940-P3-01-LQ",
    "C3-ANOX-000467-P3-36-PG",
)

DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_manual_variant_inspection_v1.json"
)
DEFAULT_MARKDOWN_PATH = Path(__file__).with_name("docs") / "pp1_manual_variant_examples_v1.md"


class ManualVariantInspectionError(ValueError):
    """Raised when a selected inspection example fails an independent check."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != DELTA_SCORE_FIELDS:
            raise ManualVariantInspectionError("DeltaScore input schema is invalid")
        rows = [dict(row) for row in reader]
    identifiers = [row["variant_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ManualVariantInspectionError("DeltaScore input has duplicate variant IDs")
    return rows


def inspect_examples(
    rows: Sequence[Mapping[str, str]],
    config: ResearchConfig,
    representative_ids: Sequence[str] = REPRESENTATIVE_VARIANT_IDS,
) -> list[dict[str, Any]]:
    """Independently recheck the manually selected representative records."""

    by_id = {row["variant_id"]: row for row in rows}
    if len(set(representative_ids)) != len(representative_ids):
        raise ManualVariantInspectionError("representative IDs must be unique")
    missing = [variant_id for variant_id in representative_ids if variant_id not in by_id]
    if missing:
        raise ManualVariantInspectionError(f"selected variants are missing: {missing}")

    predictor = DummySmokeTestPredictor()
    matrix = load_blosum62()
    examples: list[dict[str, Any]] = []
    for variant_id in representative_ids:
        row = by_id[variant_id]
        original = row["original_sequence"]
        perturbed = row["perturbed_sequence"]
        position = int(row["position"])
        original_residue = row["original_residue"]
        substituted_residue = row["substituted_residue"]
        perturbation_type = row["perturbation_type"]
        changed_positions = [
            index
            for index, (left, right) in enumerate(zip(original, perturbed), start=1)
            if left != right
        ]
        reconstructed = (
            original[: position - 1]
            + substituted_residue
            + original[position:]
        )
        stored_original_score = float(row["original_usable_score"])
        stored_perturbed_score = float(row["perturbed_usable_score"])
        recomputed_original_score = predictor.score(original)
        recomputed_perturbed_score = predictor.score(perturbed)
        stored_delta = float(row["delta_score"])
        recomputed_delta = recomputed_original_score - recomputed_perturbed_score

        p2_selection = None
        recomputed_blosum62_score: int | None = None
        if perturbation_type == "P2":
            p2_selection = select_conservative_substitution(
                original_residue,
                matrix,
                config.redox_residues,
            )
            recomputed_blosum62_score = matrix[
                (original_residue, substituted_residue)
            ]

        checks = {
            "declared_position_matches_only_change": changed_positions == [position],
            "original_residue_matches_position": (
                original[position - 1] == original_residue
            ),
            "substituted_residue_matches_position": (
                perturbed[position - 1] == substituted_residue
            ),
            "resulting_sequence_reconstructed": perturbed == reconstructed,
            "sequence_length_unchanged": len(original) == len(perturbed),
            "original_score_recomputed": math.isclose(
                stored_original_score,
                recomputed_original_score,
                rel_tol=0.0,
                abs_tol=1e-15,
            ),
            "perturbed_score_recomputed": math.isclose(
                stored_perturbed_score,
                recomputed_perturbed_score,
                rel_tol=0.0,
                abs_tol=1e-15,
            ),
            "delta_score_recomputed": math.isclose(
                stored_delta,
                recomputed_delta,
                rel_tol=0.0,
                abs_tol=1e-15,
            ),
            "p1_rule_verified": (
                perturbation_type != "P1"
                or (
                    original_residue in config.redox_residues
                    and substituted_residue == "A"
                )
            ),
            "p2_blosum62_score_verified": (
                perturbation_type != "P2"
                or (
                    p2_selection is not None
                    and p2_selection.residue == substituted_residue
                    and p2_selection.score == int(row["blosum62_score"])
                    and recomputed_blosum62_score == int(row["blosum62_score"])
                )
            ),
            "p3_seed_metadata_present": (
                perturbation_type != "P3"
                or (
                    int(row["random_seed"]) == config.random_seed
                    and bool(row["random_metadata"])
                )
            ),
        }
        if not all(checks.values()):
            failed = [name for name, passed in checks.items() if not passed]
            raise ManualVariantInspectionError(
                f"{variant_id} failed inspection checks: {failed}"
            )
        examples.append(
            {
                "variant_id": variant_id,
                "sequence_id": row["sequence_id"],
                "perturbation_type": perturbation_type,
                "original_sequence": original,
                "position": position,
                "original_residue": original_residue,
                "substituted_residue": substituted_residue,
                "mutation": f"{original_residue}{position}{substituted_residue}",
                "perturbed_sequence": perturbed,
                "blosum62_score": (
                    int(row["blosum62_score"])
                    if perturbation_type == "P2"
                    else None
                ),
                "random_seed": (
                    int(row["random_seed"])
                    if perturbation_type == "P3"
                    else None
                ),
                "original_score": stored_original_score,
                "perturbed_score": stored_perturbed_score,
                "delta_score": stored_delta,
                "absolute_delta_score": float(row["absolute_delta_score"]),
                "changed_positions": changed_positions,
                "checks": checks,
                "inspection_status": "PASS",
            }
        )
    return examples


def render_examples_markdown(report: Mapping[str, Any]) -> str:
    """Render concise human-readable evidence suitable for a PP1 demo."""

    lines = [
        "# PP1 Manually Inspected Variant Examples",
        "",
        "**Status:** PASS  ",
        "**Classification:** Software-testing evidence only  ",
        "**Warning:** Dummy predictor scores are not scientific AOP results.",
        "",
        "The six examples below were selected manually and checked row by row. "
        "The inspection was then independently revalidated against the frozen "
        "perturbation rules, Biopython BLOSUM62, and the deterministic dummy scorer.",
        "",
        "| Type | Variant | Original | Edit | Perturbed | BLOSUM62 | Original score | Perturbed score | DeltaScore |",
        "|---|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for example in report["examples"]:
        blosum = (
            str(example["blosum62_score"])
            if example["blosum62_score"] is not None
            else "N/A"
        )
        lines.append(
            "| {perturbation_type} | `{variant_id}` | `{original_sequence}` | "
            "{mutation} | `{perturbed_sequence}` | {blosum} | {original_score:.15g} | "
            "{perturbed_score:.15g} | {delta_score:.15g} |".format(
                **example,
                blosum=blosum,
            )
        )
    lines.extend(
        [
            "",
            "## Checks performed",
            "",
            "- Declared one-based position equals the only changed position.",
            "- Original and substituted residues match their sequences at that position.",
            "- The perturbed sequence is exactly reconstructed by the declared edit.",
            "- Sequence length is unchanged.",
            "- Original, perturbed, and DeltaScore values reproduce independently.",
            "- P1 examples follow redox-to-alanine rules.",
            "- P2 examples reproduce the selected residue and BLOSUM62 score.",
            "- P3 examples retain the configured master seed and random metadata.",
            "",
        ]
    )
    return "\n".join(lines)


def build_manual_variant_inspection(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    markdown_path: str | Path = DEFAULT_MARKDOWN_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Write traceable machine-readable and PP1-readable inspection evidence."""

    active_config = config or load_research_config()
    source = Path(input_path)
    report_output = Path(report_path)
    markdown_output = Path(markdown_path)
    rows = _read_rows(source)
    examples = inspect_examples(rows, active_config)
    type_counts = Counter(example["perturbation_type"] for example in examples)
    report: dict[str, Any] = {
        "schema_version": INSPECTION_SCHEMA_VERSION,
        "inspection_version": INSPECTION_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "review_mode": (
            "row-by-row manual selection and visual comparison backed by deterministic "
            "independent revalidation"
        ),
        "selection_rationale": [
            "two examples from each of P1, P2, and P3",
            "short and long peptide contexts",
            "different mutation positions and residue changes",
            "P2 examples with BLOSUM62 scores 2 and 3",
            "P3 examples with retained seed and random metadata",
        ],
        "source": {
            "path": _display_path(source),
            "dataset_version": DELTA_SCORE_DATASET_VERSION,
            "record_count": len(rows),
            "sha256": _sha256(source),
        },
        "predictor": {
            "predictor_id": rows[0]["predictor_id"],
            "display_name": rows[0]["predictor_display_name"],
            "version": rows[0]["predictor_version"],
            "scoring_method": rows[0]["scoring_method"],
            "software_testing_only": True,
            "scientific_result": False,
        },
        "examples": examples,
        "validation": {
            "status": "PASS",
            "six_examples_selected": len(examples) == 6,
            "two_examples_per_type": all(
                type_counts[kind] == 2 for kind in ("P1", "P2", "P3")
            ),
            "all_required_fields_inspected": all(
                all(example["checks"].values()) for example in examples
            ),
            "p2_scores_2_and_3_represented": {
                example["blosum62_score"]
                for example in examples
                if example["perturbation_type"] == "P2"
            }
            == {2, 3},
            "software_testing_only_preserved": True,
            "not_a_scientific_result": True,
        },
    }
    if not all(value for key, value in report["validation"].items() if key != "status"):
        raise ManualVariantInspectionError("manual inspection evidence failed validation")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(
        render_examples_markdown(report),
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    generated = build_manual_variant_inspection()
    print(
        f"Inspected {len(generated['examples'])} representative variants; "
        "all mutation, BLOSUM62, and dummy-score checks passed."
    )
