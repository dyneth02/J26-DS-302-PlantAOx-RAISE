"""Run reproducible CD-HIT clustering for Task 3.7."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

from .cleaning import CLEANED_DATASET_VERSION, OUTPUT_FIELDS as CLEANED_FIELDS
from .config import ResearchConfig, load_research_config
from .standardization import REPOSITORY_ROOT


DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "cleaned_aop_sequences_v1.csv"
)
DEFAULT_FASTA_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "cd_hit_input_v1.fasta"
)
DEFAULT_REPRESENTATIVE_FASTA_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "cd_hit_representatives_90_v1.fasta"
)
DEFAULT_REPRESENTATIVE_CSV_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "cd_hit_representatives_90_v1.csv"
)
DEFAULT_CLUSTER_CSV_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "cd_hit_clusters_90_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "cd_hit_deduplication_report_v1.json"
)
DEFAULT_CDHIT_COMMAND = ("wsl.exe", "-d", "Ubuntu-24.04", "--", "cd-hit")
CD_HIT_DATASET_VERSION = "c3_aop_bcs_cd_hit_90_v1"

REPRESENTATIVE_FIELDS = (*CLEANED_FIELDS, "cd_hit_cluster_id", "cd_hit_cluster_size")
CLUSTER_FIELDS = (
    "cd_hit_cluster_id",
    "cluster_member_index",
    "sequence_id",
    "sequence_length",
    "is_representative",
    "identity_to_representative_percent",
)

_CLUSTER_HEADER = re.compile(r"^>Cluster (\d+)$")
_CLUSTER_MEMBER = re.compile(r"^(\d+)\s+(\d+)aa,\s+>(.+?)\.\.\.\s+(.+)$")
_IDENTITY_PERCENT = re.compile(r"([0-9]+(?:\.[0-9]+)?)%$")
_VERSION = re.compile(r"CD-HIT version\s+([^\s]+)")


def read_cleaned_records(input_path: str | Path = DEFAULT_INPUT_PATH) -> list[dict[str, str]]:
    """Read and validate the cleaned Task 3.6 table contract."""

    path = Path(input_path)
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != CLEANED_FIELDS:
            raise ValueError("Cleaned input schema does not match the Task 3.6 contract")
        records = list(reader)

    sequence_ids = [record["sequence_id"] for record in records]
    if len(sequence_ids) != len(set(sequence_ids)):
        raise ValueError("Cleaned input contains duplicate sequence identifiers")
    return records


def write_fasta(records: Iterable[Mapping[str, Any]], output_path: str | Path) -> int:
    """Write deterministic one-line FASTA records and return their count."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="ascii", newline="\n") as fasta_file:
        for record in records:
            sequence_id = str(record.get("sequence_id") or "")
            sequence = str(record.get("peptide_sequence") or "")
            if not sequence_id or any(character.isspace() for character in sequence_id):
                raise ValueError(f"Invalid FASTA sequence identifier: {sequence_id!r}")
            if not sequence:
                raise ValueError(f"Missing peptide sequence for {sequence_id}")
            fasta_file.write(f">{sequence_id}\n{sequence}\n")
            count += 1
    return count


def read_fasta(path: str | Path) -> list[tuple[str, str]]:
    """Read simple FASTA while accepting wrapped sequence lines."""

    records: list[tuple[str, str]] = []
    sequence_id: str | None = None
    sequence_parts: list[str] = []
    with Path(path).open("r", encoding="ascii") as fasta_file:
        for raw_line in fasta_file:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if sequence_id is not None:
                    records.append((sequence_id, "".join(sequence_parts)))
                sequence_id = line[1:].split()[0]
                sequence_parts = []
            elif sequence_id is None:
                raise ValueError("FASTA sequence appears before its identifier")
            else:
                sequence_parts.append(line)
    if sequence_id is not None:
        records.append((sequence_id, "".join(sequence_parts)))
    return records


def parse_cd_hit_clusters(path: str | Path) -> list[dict[str, str | int]]:
    """Parse CD-HIT's native .clstr output into a stable tabular representation."""

    memberships: list[dict[str, str | int]] = []
    cluster_id: int | None = None
    for line_number, raw_line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        header_match = _CLUSTER_HEADER.fullmatch(raw_line)
        if header_match:
            cluster_id = int(header_match.group(1))
            continue

        member_match = _CLUSTER_MEMBER.fullmatch(raw_line)
        if cluster_id is None or member_match is None:
            raise ValueError(f"Malformed CD-HIT cluster output at line {line_number}")

        marker = member_match.group(4)
        is_representative = marker == "*"
        identity_match = _IDENTITY_PERCENT.search(marker)
        if not is_representative and identity_match is None:
            raise ValueError(f"Missing CD-HIT identity at line {line_number}")
        memberships.append(
            {
                "cd_hit_cluster_id": cluster_id,
                "cluster_member_index": int(member_match.group(1)),
                "sequence_id": member_match.group(3),
                "sequence_length": int(member_match.group(2)),
                "is_representative": "true" if is_representative else "false",
                "identity_to_representative_percent": (
                    "100.00" if is_representative else identity_match.group(1)
                ),
            }
        )
    return memberships


def _windows_to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        raise ValueError(f"CD-HIT WSL input must be on a Windows drive: {resolved}")
    relative = resolved.as_posix()[len(resolved.drive) :].lstrip("/")
    return f"/mnt/{drive}/{relative}"


def _cd_hit_arguments(
    input_fasta: Path,
    output_fasta: Path,
    config: ResearchConfig,
) -> list[str]:
    return [
        "-i",
        _windows_to_wsl_path(input_fasta),
        "-o",
        _windows_to_wsl_path(output_fasta),
        "-c",
        f"{config.cd_hit_identity_threshold:.2f}",
        "-n",
        "2",
        "-G",
        "1",
        "-g",
        "1",
        "-l",
        str(config.sequence_min_length - 1),
        "-d",
        "0",
        "-T",
        "1",
        "-M",
        "800",
    ]


def get_cd_hit_version(command: Sequence[str] = DEFAULT_CDHIT_COMMAND) -> str:
    result = subprocess.run(
        [*command, "-h"],
        check=False,
        capture_output=True,
        text=True,
    )
    version_match = _VERSION.search(result.stdout + result.stderr)
    if version_match is None:
        raise RuntimeError("Could not determine the installed CD-HIT version")
    return version_match.group(1)


def run_cd_hit(
    input_fasta: str | Path,
    output_fasta: str | Path,
    config: ResearchConfig,
    command: Sequence[str] = DEFAULT_CDHIT_COMMAND,
) -> tuple[str, list[str]]:
    """Run the real CD-HIT executable and return its version and fixed arguments."""

    input_path = Path(input_fasta)
    output_path = Path(output_fasta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    arguments = _cd_hit_arguments(input_path, output_path, config)
    version = get_cd_hit_version(command)
    result = subprocess.run(
        [*command, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = (result.stdout + "\n" + result.stderr).strip()
        raise RuntimeError(f"CD-HIT failed with exit code {result.returncode}: {details}")
    cluster_path = Path(f"{output_path}.clstr")
    if not output_path.is_file() or not cluster_path.is_file():
        raise RuntimeError("CD-HIT did not create both representative FASTA and .clstr outputs")
    return version, arguments


def _write_csv(
    records: Iterable[Mapping[str, Any]],
    output_path: Path,
    fieldnames: tuple[str, ...],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def build_representative_records(
    cleaned_records: Sequence[Mapping[str, Any]],
    representative_fasta_records: Sequence[tuple[str, str]],
    memberships: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Join CD-HIT representatives back to the complete cleaned-record schema."""

    cleaned_by_id = {str(record["sequence_id"]): dict(record) for record in cleaned_records}
    input_ids = set(cleaned_by_id)
    membership_ids = [str(member["sequence_id"]) for member in memberships]
    if len(membership_ids) != len(set(membership_ids)) or set(membership_ids) != input_ids:
        raise ValueError("CD-HIT cluster membership does not cover each cleaned record exactly once")

    representatives_by_cluster: dict[int, str] = {}
    cluster_sizes: dict[int, int] = {}
    cluster_by_member: dict[str, int] = {}
    for member in memberships:
        cluster_id = int(member["cd_hit_cluster_id"])
        sequence_id = str(member["sequence_id"])
        cluster_by_member[sequence_id] = cluster_id
        cluster_sizes[cluster_id] = cluster_sizes.get(cluster_id, 0) + 1
        if member["is_representative"] == "true":
            if cluster_id in representatives_by_cluster:
                raise ValueError(f"Cluster {cluster_id} has multiple representatives")
            representatives_by_cluster[cluster_id] = sequence_id

    representative_ids = [sequence_id for sequence_id, _ in representative_fasta_records]
    if len(representative_ids) != len(set(representative_ids)):
        raise ValueError("CD-HIT representative FASTA contains duplicate identifiers")
    if set(representative_ids) != set(representatives_by_cluster.values()):
        raise ValueError("Representative FASTA and .clstr representatives do not agree")

    output: list[dict[str, Any]] = []
    for sequence_id, sequence in representative_fasta_records:
        source = cleaned_by_id.get(sequence_id)
        if source is None or source["peptide_sequence"] != sequence:
            raise ValueError(f"Representative sequence mismatch for {sequence_id}")
        cluster_id = cluster_by_member[sequence_id]
        output.append(
            {
                **source,
                "cd_hit_cluster_id": cluster_id,
                "cd_hit_cluster_size": cluster_sizes[cluster_id],
            }
        )
    return output


def _display_path(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix() if path.is_relative_to(REPOSITORY_ROOT) else str(path)


def _artifact(path: Path, record_count: int) -> dict[str, str | int]:
    return {
        "path": _display_path(path),
        "record_count": record_count,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_cd_hit_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    fasta_path: str | Path = DEFAULT_FASTA_PATH,
    representative_fasta_path: str | Path = DEFAULT_REPRESENTATIVE_FASTA_PATH,
    representative_csv_path: str | Path = DEFAULT_REPRESENTATIVE_CSV_PATH,
    cluster_csv_path: str | Path = DEFAULT_CLUSTER_CSV_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    command: Sequence[str] = DEFAULT_CDHIT_COMMAND,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Build all Task 3.7 CD-HIT artifacts and a reproducibility report."""

    input_path = Path(input_path)
    fasta_path = Path(fasta_path)
    representative_fasta_path = Path(representative_fasta_path)
    representative_csv_path = Path(representative_csv_path)
    cluster_csv_path = Path(cluster_csv_path)
    report_path = Path(report_path)
    active_config = config or load_research_config()

    records = read_cleaned_records(input_path)
    input_count = write_fasta(records, fasta_path)
    version, arguments = run_cd_hit(
        fasta_path,
        representative_fasta_path,
        active_config,
        command,
    )
    cluster_path = Path(f"{representative_fasta_path}.clstr")
    representative_fasta_records = read_fasta(representative_fasta_path)
    memberships = parse_cd_hit_clusters(cluster_path)
    representatives = build_representative_records(
        records,
        representative_fasta_records,
        memberships,
    )
    _write_csv(representatives, representative_csv_path, REPRESENTATIVE_FIELDS)
    _write_csv(memberships, cluster_csv_path, CLUSTER_FIELDS)

    cluster_ids = {int(member["cd_hit_cluster_id"]) for member in memberships}
    counts = {
        "input_count": input_count,
        "representative_count": len(representatives),
        "cluster_count": len(cluster_ids),
        "removed_at_90_percent_identity": input_count - len(representatives),
    }
    if counts["representative_count"] != counts["cluster_count"]:
        raise RuntimeError("CD-HIT representative and cluster counts do not match")

    report = {
        "schema_version": "1.0",
        "dataset_version": CD_HIT_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": CLEANED_DATASET_VERSION,
        "source": {
            "path": _display_path(input_path),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "tool": {
            "name": "CD-HIT",
            "version": version,
            "runtime": "Ubuntu-24.04 WSL /usr/bin/cd-hit",
        },
        "parameters": {
            "identity_threshold": active_config.cd_hit_identity_threshold,
            "identity_definition": "CD-HIT global identity over the shorter sequence",
            "word_length": 2,
            "accurate_mode": True,
            "throw_away_length": active_config.sequence_min_length - 1,
            "minimum_retained_sequence_length": active_config.sequence_min_length,
            "description_length": 0,
            "threads": 1,
            "memory_megabytes": 800,
        },
        "command": [*command, *arguments],
        "counts": counts,
        "outputs": {
            "input_fasta": _artifact(fasta_path, input_count),
            "representative_fasta": _artifact(
                representative_fasta_path,
                len(representative_fasta_records),
            ),
            "native_cluster_file": _artifact(cluster_path, len(cluster_ids)),
            "representative_table": _artifact(representative_csv_path, len(representatives)),
            "cluster_membership_table": _artifact(cluster_csv_path, len(memberships)),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as report_file:
        report_file.write(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    report = build_cd_hit_dataset()
    counts = report["counts"]
    print(
        f'CD-HIT clustered {counts["input_count"]} sequences into '
        f'{counts["cluster_count"]} clusters and retained '
        f'{counts["representative_count"]} representatives.'
    )


if __name__ == "__main__":
    main()
