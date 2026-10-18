"""Standardize acquired AOP candidate records without validating or filtering sequences."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROVENANCE_PATH = REPOSITORY_ROOT / "data" / "raw" / "c3_aop_bcs" / "PROVENANCE.json"
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT / "data" / "interim" / "c3_aop_bcs" / "standardized_aop_candidates_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT / "data" / "interim" / "c3_aop_bcs" / "standardization_report_v1.json"
)
STANDARDIZED_DATASET_VERSION = "c3_aop_bcs_standardized_v1"

OUTPUT_FIELDS = (
    "sequence_id",
    "peptide_sequence",
    "source",
    "source_record_id",
    "evidence_tier_candidate",
    "evidence_basis",
    "source_reference",
    "source_label",
    "frs",
    "chelator",
    "raw_file",
    "raw_row_number",
)

SOURCE_SPECS = {
    "AnOxPePred supplementary assay table": {
        "code": "ANOX",
        "source": "AnOxPePred",
        "sequence_field": "Sequence",
        "record_id_field": "",
        "evidence_tier_candidate": "E1",
        "evidence_basis": "direct_assay_positive",
    },
    "Multi-AOP AnOxPePred benchmark": {
        "code": "MAOP-ANOX",
        "source": "Multi-AOP:AnOxPePred",
        "sequence_field": "SEQUENCE",
        "record_id_field": "name",
        "evidence_tier_candidate": "E2",
        "evidence_basis": "benchmark_positive_label",
    },
    "Multi-AOP AnOxPP benchmark": {
        "code": "MAOP-ANOXPP",
        "source": "Multi-AOP:AnOxPP",
        "sequence_field": "SEQUENCE",
        "record_id_field": "name",
        "evidence_tier_candidate": "E2",
        "evidence_basis": "benchmark_positive_label",
    },
    "Multi-AOP AOPP benchmark": {
        "code": "MAOP-AOPP",
        "source": "Multi-AOP:AOPP",
        "sequence_field": "SEQUENCE",
        "record_id_field": "name",
        "evidence_tier_candidate": "E2",
        "evidence_basis": "benchmark_positive_label",
    },
}


def normalize_sequence(value: str | None) -> str:
    """Uppercase a sequence and remove all embedded or surrounding whitespace."""

    return "" if value is None else "".join(value.split()).upper()


def _is_candidate(row: dict[str, str | None], dataset: str) -> bool:
    if dataset == "AnOxPePred supplementary assay table":
        return row.get("FRS") == "1" or row.get("Chelator") == "1"
    return row.get("label") == "1"


def _repository_reference(source: dict[str, Any]) -> str:
    return (
        f'{source["repository_url"]}/blob/{source["upstream_branch"]}/'
        f'{source["upstream_path"]}'
    )


def standardize_sources(
    provenance_path: str | Path = DEFAULT_PROVENANCE_PATH,
) -> list[dict[str, str | int]]:
    """Load candidate-positive raw rows into the common Task 3.5 schema.

    This intentionally performs no alphabet, length, duplicate, conflict, or redox
    eligibility checks; those belong to Tasks 3.6 through 3.8.
    """

    manifest_path = Path(provenance_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_version") != "c3_aop_bcs_raw_v1":
        raise ValueError("Unsupported or missing raw C3 dataset version")

    repository_root = manifest_path.resolve().parents[3]
    standardized: list[dict[str, str | int]] = []

    for source in manifest["sources"]:
        dataset = source["dataset"]
        try:
            spec = SOURCE_SPECS[dataset]
        except KeyError as exc:
            raise ValueError(f"Unsupported C3 source dataset: {dataset!r}") from exc

        raw_path = repository_root / source["local_path"]
        source_sequence_number = 0
        with raw_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for raw_row_number, row in enumerate(reader, start=2):
                if not _is_candidate(row, dataset):
                    continue

                source_sequence_number += 1
                row_reference = row.get("Source") or _repository_reference(source)
                standardized.append(
                    {
                        "sequence_id": f'C3-{spec["code"]}-{source_sequence_number:06d}',
                        "peptide_sequence": normalize_sequence(row.get(spec["sequence_field"])),
                        "source": spec["source"],
                        "source_record_id": row.get(spec["record_id_field"]) or "",
                        "evidence_tier_candidate": spec["evidence_tier_candidate"],
                        "evidence_basis": spec["evidence_basis"],
                        "source_reference": row_reference,
                        "source_label": row.get("label") or "",
                        "frs": row.get("FRS") or "",
                        "chelator": row.get("Chelator") or "",
                        "raw_file": source["local_path"],
                        "raw_row_number": raw_row_number,
                    }
                )

    return standardized


def _write_csv(records: Iterable[dict[str, str | int]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def build_standardized_dataset(
    provenance_path: str | Path = DEFAULT_PROVENANCE_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Create the standardized intermediate CSV and its reproducibility report."""

    provenance_path = Path(provenance_path)
    output_path = Path(output_path)
    report_path = Path(report_path)
    records = standardize_sources(provenance_path)
    _write_csv(records, output_path)

    output_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    source_counts = Counter(str(record["source"]) for record in records)
    report = {
        "schema_version": "1.0",
        "dataset_version": STANDARDIZED_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": "c3_aop_bcs_raw_v1",
        "record_count": len(records),
        "source_record_counts": dict(source_counts),
        "output_schema": list(OUTPUT_FIELDS),
        "normalization": ["convert sequence to uppercase", "remove all sequence whitespace"],
        "selection": [
            "AnOxPePred rows where FRS=1 or Chelator=1",
            "Multi-AOP benchmark rows where label=1",
        ],
        "deferred_to_task_3_6": [
            "missing-sequence rejection",
            "amino-acid alphabet validation",
            "3-50 amino-acid length filtering",
            "exact duplicate removal",
            "cross-source conflict resolution",
        ],
        "output": {
            "path": output_path.relative_to(REPOSITORY_ROOT).as_posix()
            if output_path.is_relative_to(REPOSITORY_ROOT)
            else str(output_path),
            "sha256": output_hash,
        },
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    report = build_standardized_dataset()
    print(
        f'Wrote {report["record_count"]} records to {report["output"]["path"]} '
        f'(SHA-256 {report["output"]["sha256"]})'
    )


if __name__ == "__main__":
    main()
