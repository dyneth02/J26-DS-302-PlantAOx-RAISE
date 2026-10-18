"""Production-scale reproducibility checks for the C3 perturbation workflow."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import platform
import tempfile
from typing import Any

import Bio

from .blosum62 import DEFAULT_MANIFEST_PATH as BLOSUM62_MANIFEST_PATH
from .config import DEFAULT_CONFIG_PATH, ResearchConfig, load_research_config
from .p1_alanine_scanning import P1_DATASET_VERSION
from .p2_conservative_substitutions import P2_DATASET_VERSION
from .p3_random_controls import P3_DATASET_VERSION
from .perturbation_pipeline import (
    COMBINED_DATASET_VERSION,
    DEFAULT_INPUT_PATH,
    PIPELINE_VERSION,
    build_combined_perturbation_dataset,
)
from .perturbation_schema import PERTURBATION_FIELDS, PERTURBATION_SCHEMA_VERSION
from .standardization import REPOSITORY_ROOT


DEFAULT_EVIDENCE_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "perturbation_reproducibility_report_v1.json"
)
REPRODUCIBILITY_EVIDENCE_VERSION = "c3_aop_bcs_perturbation_reproducibility_v1"


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_evidence(path: Path, record_count: int) -> dict[str, str | int]:
    return {
        "record_count": record_count,
        "byte_count": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _p3_evidence(combined_path: Path) -> dict[str, str | int]:
    with combined_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != PERTURBATION_FIELDS:
            raise ValueError("Combined output does not use the frozen perturbation schema")
        p3_rows = [row for row in reader if row["perturbation_type"] == "P3"]

    text_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        text_buffer,
        fieldnames=PERTURBATION_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(p3_rows)
    content = text_buffer.getvalue().encode("utf-8")
    return {
        "record_count": len(p3_rows),
        "byte_count": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _config_values(config: ResearchConfig) -> dict[str, object]:
    return {
        "random_seed": config.random_seed,
        "sequence_min_length": config.sequence_min_length,
        "sequence_max_length": config.sequence_max_length,
        "redox_residues": list(config.redox_residues),
        "cd_hit_identity_threshold": config.cd_hit_identity_threshold,
        "primary_delta": config.primary_delta,
        "sensitivity_deltas": list(config.sensitivity_deltas),
        "pilot_dataset_size": config.pilot_dataset_size,
    }


def _run_pipeline(
    run_id: str,
    run_directory: Path,
    input_path: Path,
    config: ResearchConfig,
    created_on: date,
) -> dict[str, Any]:
    run_directory.mkdir(parents=True, exist_ok=True)
    accepted_path = run_directory / "accepted.csv"
    rejection_path = run_directory / "rejections.csv"
    pipeline_report_path = run_directory / "pipeline_report.json"
    pipeline_report = build_combined_perturbation_dataset(
        input_path=input_path,
        output_path=accepted_path,
        rejection_path=rejection_path,
        report_path=pipeline_report_path,
        config=config,
        created_on=created_on,
    )
    counts = pipeline_report["counts"]
    versions = {
        "pipeline": pipeline_report["pipeline_version"],
        "combined_dataset": pipeline_report["dataset_version"],
        "perturbation_schema": pipeline_report["perturbation_schema"]["version"],
        "generators": pipeline_report["generator_dataset_versions"],
    }
    return {
        "run_id": run_id,
        "configuration": pipeline_report["research_config"]["values"],
        "versions": versions,
        "counts": counts,
        "artifacts": {
            "accepted_perturbations": _file_evidence(
                accepted_path,
                counts["accepted_variant_count"],
            ),
            "rejected_perturbations": _file_evidence(
                rejection_path,
                counts["rejected_variant_count"],
            ),
            "p3_random_controls": _p3_evidence(accepted_path),
        },
    }


def create_reproducibility_evidence(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    evidence_path: str | Path = DEFAULT_EVIDENCE_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Run the production perturbation workflow twice and record exact comparisons."""

    input_path = Path(input_path)
    evidence_path = Path(evidence_path)
    active_config = config or load_research_config()
    evidence_date = created_on or date.today()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="c3_aop_bcs_reproducibility_",
        dir=evidence_path.parent,
    ) as directory:
        temporary = Path(directory)
        run_1 = _run_pipeline(
            "run_1",
            temporary / "run_1",
            input_path,
            active_config,
            evidence_date,
        )
        run_2 = _run_pipeline(
            "run_2",
            temporary / "run_2",
            input_path,
            active_config,
            evidence_date,
        )

    comparisons = {
        "accepted_perturbations_byte_identical": (
            run_1["artifacts"]["accepted_perturbations"]
            == run_2["artifacts"]["accepted_perturbations"]
        ),
        "rejection_ledgers_byte_identical": (
            run_1["artifacts"]["rejected_perturbations"]
            == run_2["artifacts"]["rejected_perturbations"]
        ),
        "p3_random_controls_byte_identical": (
            run_1["artifacts"]["p3_random_controls"]
            == run_2["artifacts"]["p3_random_controls"]
        ),
        "counts_identical": run_1["counts"] == run_2["counts"],
        "configuration_identical": (
            run_1["configuration"] == run_2["configuration"]
        ),
        "versions_identical": run_1["versions"] == run_2["versions"],
        "master_seed_identical": (
            run_1["configuration"]["random_seed"]
            == run_2["configuration"]["random_seed"]
            == active_config.random_seed
        ),
    }
    comparisons["all_checks_passed"] = all(comparisons.values())

    evidence = {
        "schema_version": "1.0",
        "evidence_version": REPRODUCIBILITY_EVIDENCE_VERSION,
        "created_on": evidence_date.isoformat(),
        "result": "PASS" if comparisons["all_checks_passed"] else "FAIL",
        "input": {
            "path": _display_path(input_path),
            "byte_count": input_path.stat().st_size,
            "sha256": _sha256(input_path),
        },
        "configuration": {
            "source": (
                _display_path(DEFAULT_CONFIG_PATH)
                if config is None
                else "provided ResearchConfig object"
            ),
            "sha256": _sha256(DEFAULT_CONFIG_PATH) if config is None else None,
            "values": _config_values(active_config),
        },
        "software_versions": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "biopython": Bio.__version__,
            "pipeline": PIPELINE_VERSION,
            "combined_dataset": COMBINED_DATASET_VERSION,
            "perturbation_schema": PERTURBATION_SCHEMA_VERSION,
            "generators": {
                "P1": P1_DATASET_VERSION,
                "P2": P2_DATASET_VERSION,
                "P3": P3_DATASET_VERSION,
            },
        },
        "support_artifacts": {
            "blosum62_manifest": {
                "path": _display_path(BLOSUM62_MANIFEST_PATH),
                "sha256": _sha256(BLOSUM62_MANIFEST_PATH),
            },
        },
        "run_count": 2,
        "runs": [run_1, run_2],
        "comparisons": comparisons,
    }
    with evidence_path.open("w", encoding="utf-8", newline="\n") as evidence_file:
        evidence_file.write(json.dumps(evidence, indent=2) + "\n")
    if not comparisons["all_checks_passed"]:
        raise RuntimeError(
            f"Perturbation reproducibility checks failed; see {evidence_path}"
        )
    return evidence


def main() -> None:
    evidence = create_reproducibility_evidence()
    accepted = evidence["runs"][0]["counts"]["accepted_variant_count"]
    p3_count = evidence["runs"][0]["artifacts"]["p3_random_controls"][
        "record_count"
    ]
    print(
        f"Reproducibility {evidence['result']}: two runs produced {accepted} identical "
        f"accepted perturbations, including {p3_count} identical P3 controls."
    )


if __name__ == "__main__":
    main()
