"""Read-only PP1 release inventory and offline verification for Component 02.

The ``create`` command writes only the new release manifest and inventory.
The ``verify`` command does not mutate accepted datasets, caches, experiment
directories, or reports.  It verifies bytes first, then exercises the accepted
fold-0 cache and selected PyTorch checkpoints without fitting anything.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


RELEASE_ID = "c2_pp1_freeze_v1"
MANIFEST_RELATIVE_PATH = Path("data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json")
INVENTORY_RELATIVE_PATH = Path("data/processed/c2_pu/C2_PP1_ARTIFACT_INVENTORY.csv")
ESSENTIAL_IGNORED_COUNT = 56
PRESERVATION_ARCHIVE_NAME = f"{RELEASE_ID}-essential-artifacts.zip"
PRESERVATION_VERIFICATION_NAME = f"{RELEASE_ID}-essential-artifacts.verification.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(path: Path, repo_root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"Release artifact is outside the repository: {resolved}") from exc


def _git(*args: str, repo_root: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=check,
    )


def _git_disposition(relative_path: str, repo_root: Path) -> str:
    tracked = _git("ls-files", "--error-unmatch", "--", relative_path, repo_root=repo_root, check=False)
    if tracked.returncode == 0:
        return "tracked"
    ignored = _git("check-ignore", "-q", "--", relative_path, repo_root=repo_root, check=False)
    return "ignored" if ignored.returncode == 0 else "untracked"


def _load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _preservation_records(repo_root: Path, manifest_path: Path) -> tuple[dict, list[dict]]:
    """Load the manifest-bound inventory rows that must be preserved as bytes."""

    repo_root = Path(repo_root).resolve()
    manifest_path = Path(manifest_path)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    manifest = _load_json(manifest_path)
    if manifest["release"]["id"] != RELEASE_ID:
        raise ValueError(f"Unexpected release id: {manifest['release']['id']}")
    inventory_meta = manifest["artifact_inventory"]
    inventory_path = repo_root / inventory_meta["path"]
    if sha256_file(inventory_path) != inventory_meta["sha256"]:
        raise ValueError("Artifact inventory SHA-256 does not match the release manifest")
    with inventory_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    records = [
        row
        for row in rows
        if row["git_disposition"] == "ignored" and row["retention"] == "essential_to_retain_as_bytes"
    ]
    if len(records) != ESSENTIAL_IGNORED_COUNT:
        raise ValueError(
            f"Expected {ESSENTIAL_IGNORED_COUNT} essential ignored artifacts, found {len(records)}"
        )
    if len({row["path"] for row in records}) != len(records):
        raise ValueError("Preservation inventory contains duplicate repository-relative paths")
    if any(Path(row["path"]).is_absolute() or ".." in Path(row["path"]).parts for row in records):
        raise ValueError("Preservation inventory contains a non-portable or unsafe path")
    return manifest, sorted(records, key=lambda row: row["path"])


def _verify_archive_members(archive_path: Path, records: list[dict]) -> dict:
    expected = {row["path"]: row for row in records}
    verified_bytes = 0
    with zipfile.ZipFile(archive_path, "r") as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)):
            raise ValueError("Preservation archive contains duplicate member paths")
        if set(names) != set(expected):
            missing = sorted(set(expected) - set(names))
            unexpected = sorted(set(names) - set(expected))
            raise ValueError(f"Preservation archive membership mismatch: missing={missing}, unexpected={unexpected}")
        for member in members:
            record = expected[member.filename]
            expected_size = int(record["size_bytes"])
            if member.file_size != expected_size:
                raise ValueError(f"Preservation archive size mismatch: {member.filename}")
            digest = hashlib.sha256()
            with archive.open(member, "r") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != record["sha256"]:
                raise ValueError(f"Preservation archive SHA-256 mismatch: {member.filename}")
            verified_bytes += member.file_size
    return {"artifact_count": len(records), "uncompressed_bytes": verified_bytes}


def create_preservation_package(repo_root: Path, manifest_path: Path, destination: Path) -> dict:
    """Copy the 56 essential ignored artifacts into a verified, path-preserving ZIP."""

    repo_root = Path(repo_root).resolve()
    destination = Path(destination).resolve()
    try:
        destination.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise ValueError("Preservation destination must be outside the repository")
    if not destination.is_dir():
        raise ValueError(f"Preservation destination must already exist as a directory: {destination}")

    manifest, records = _preservation_records(repo_root, manifest_path)
    total_bytes = sum(int(row["size_bytes"]) for row in records)
    free_bytes = shutil.disk_usage(destination).free
    if free_bytes < total_bytes * 2:
        raise ValueError(
            f"Insufficient free space at preservation destination: need at least {total_bytes * 2}, "
            f"found {free_bytes}"
        )
    for record in records:
        source = repo_root / record["path"]
        if not source.is_file():
            raise ValueError(f"Essential preservation source is missing: {record['path']}")
        if source.stat().st_size != int(record["size_bytes"]) or sha256_file(source) != record["sha256"]:
            raise ValueError(f"Essential preservation source differs from inventory: {record['path']}")

    archive_path = destination / PRESERVATION_ARCHIVE_NAME
    verification_path = destination / PRESERVATION_VERIFICATION_NAME
    if archive_path.exists() or verification_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite an existing preservation package: {archive_path} or {verification_path}"
        )
    temporary_archive = destination / f".{PRESERVATION_ARCHIVE_NAME}.tmp"
    if temporary_archive.exists():
        raise FileExistsError(f"Temporary preservation path already exists: {temporary_archive}")

    try:
        with zipfile.ZipFile(
            temporary_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True
        ) as archive:
            for record in records:
                info = zipfile.ZipInfo(record["path"], date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100644 & 0xFFFF) << 16
                with (repo_root / record["path"]).open("rb") as source, archive.open(info, "w") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
        archive_check = _verify_archive_members(temporary_archive, records)
        os.replace(temporary_archive, archive_path)
    finally:
        if temporary_archive.exists():
            temporary_archive.unlink()

    inventory_path = repo_root / manifest["artifact_inventory"]["path"]
    verification = {
        "schema_version": "c2_pp1_preservation_verification_v1",
        "release_id": RELEASE_ID,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "manifest_path": _repo_relative(
                Path(manifest_path) if Path(manifest_path).is_absolute() else repo_root / manifest_path,
                repo_root,
            ),
            "inventory_path": _repo_relative(inventory_path, repo_root),
            "inventory_sha256": sha256_file(inventory_path),
        },
        "archive": {
            "filename": archive_path.name,
            "size_bytes": archive_path.stat().st_size,
            "sha256": sha256_file(archive_path),
            **archive_check,
            "repository_relative_paths_preserved": True,
        },
        "destination": {
            "nonportable_local_directory": str(destination),
            "classification": "owner_supplied_external_backup_destination",
        },
        "artifacts": [
            {"path": row["path"], "size_bytes": int(row["size_bytes"]), "sha256": row["sha256"]}
            for row in records
        ],
        "verification_status": "PASS",
    }
    verification_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {
        "release_id": RELEASE_ID,
        "archive": str(archive_path),
        "archive_sha256": verification["archive"]["sha256"],
        "archive_size_bytes": verification["archive"]["size_bytes"],
        "verification_record": str(verification_path),
        "verification_record_sha256": sha256_file(verification_path),
        "artifact_count": archive_check["artifact_count"],
        "uncompressed_bytes": archive_check["uncompressed_bytes"],
        "status": "PASS",
    }


def verify_preservation_package(
    repo_root: Path, manifest_path: Path, archive_path: Path, verification_path: Path
) -> dict:
    """Independently verify a completed package against the manifest-bound inventory."""

    repo_root = Path(repo_root).resolve()
    manifest, records = _preservation_records(repo_root, manifest_path)
    archive_path = Path(archive_path).resolve()
    verification_path = Path(verification_path).resolve()
    verification = _load_json(verification_path)
    if verification.get("release_id") != RELEASE_ID or verification.get("verification_status") != "PASS":
        raise ValueError("Preservation verification record has an invalid release identity or status")
    inventory_path = repo_root / manifest["artifact_inventory"]["path"]
    if verification["source"]["inventory_sha256"] != sha256_file(inventory_path):
        raise ValueError("Preservation verification record refers to a different inventory")
    if verification["archive"]["filename"] != archive_path.name:
        raise ValueError("Preservation verification record refers to a different archive filename")
    if verification["archive"]["size_bytes"] != archive_path.stat().st_size:
        raise ValueError("Preservation archive size differs from the verification record")
    archive_sha256 = sha256_file(archive_path)
    if verification["archive"]["sha256"] != archive_sha256:
        raise ValueError("Preservation archive SHA-256 differs from the verification record")
    expected_artifacts = [
        {"path": row["path"], "size_bytes": int(row["size_bytes"]), "sha256": row["sha256"]}
        for row in records
    ]
    if verification["artifacts"] != expected_artifacts:
        raise ValueError("Preservation verification record artifact list differs from the inventory")
    archive_check = _verify_archive_members(archive_path, records)
    return {
        "release_id": RELEASE_ID,
        "archive": str(archive_path),
        "archive_sha256": archive_sha256,
        "verification_record": str(verification_path),
        "verification_record_sha256": sha256_file(verification_path),
        **archive_check,
        "status": "PASS",
    }


def _verify_directory_records(backup_root: Path, records: list[dict]) -> dict:
    backup_root = Path(backup_root).resolve()
    if not backup_root.is_dir():
        raise ValueError(f"Backup root does not exist as a directory: {backup_root}")
    failures: list[dict] = []
    verified_bytes = 0
    path_mode: str | None = None
    for record in records:
        relative = Path(record["path"])
        candidates = [("repository_root_copy", backup_root / relative)]
        if relative.parts and relative.parts[0] == "data":
            candidates.append(("data_directory_copy", backup_root.joinpath(*relative.parts[1:])))
        existing = [(mode, path) for mode, path in candidates if path.is_file()]
        if not existing:
            failures.append({"path": record["path"], "reason": "missing"})
            continue
        mode, path = existing[0]
        if path_mode is None:
            path_mode = mode
        elif path_mode != mode:
            failures.append({"path": record["path"], "reason": "inconsistent_backup_layout"})
            continue
        expected_size = int(record["size_bytes"])
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            failures.append(
                {
                    "path": record["path"],
                    "reason": "size_mismatch",
                    "expected_size": expected_size,
                    "actual_size": actual_size,
                }
            )
            continue
        actual_sha256 = sha256_file(path)
        if actual_sha256 != record["sha256"]:
            failures.append(
                {
                    "path": record["path"],
                    "reason": "sha256_mismatch",
                    "expected_sha256": record["sha256"],
                    "actual_sha256": actual_sha256,
                }
            )
            continue
        verified_bytes += actual_size
    result = {
        "release_id": RELEASE_ID,
        "backup_root": str(backup_root),
        "backup_layout": path_mode,
        "artifact_count_expected": len(records),
        "artifact_count_verified": len(records) - len(failures),
        "verified_bytes": verified_bytes,
        "failures": failures,
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "PASS" if not failures else "FAIL",
    }
    if failures:
        raise ValueError("Backup-directory verification failed: " + json.dumps(result, indent=2))
    return result


def verify_preservation_directory(repo_root: Path, manifest_path: Path, backup_root: Path) -> dict:
    """Verify an existing copied data tree without creating or modifying backup files."""

    repo_root = Path(repo_root).resolve()
    _, records = _preservation_records(repo_root, manifest_path)
    return _verify_directory_records(backup_root, records)


def _accepted_artifact_specs(repo_root: Path) -> list[dict]:
    """Return the bounded PP1 release inventory, excluding scratch/failed runs."""

    processed = repo_root / "data/processed/c2_pu"
    interim = repo_root / "data/interim/c2_pu"
    docs = repo_root / "src/plantaox/c2_pu/docs"
    specs: dict[str, dict] = {}

    def add(
        path: Path,
        category: str,
        retention: str,
        required_for: str,
        recovery: str,
        source_type: str = "project_generated",
    ) -> None:
        relative = _repo_relative(path, repo_root)
        specs[relative] = {
            "path": relative,
            "category": category,
            "retention": retention,
            "required_for": required_for,
            "recovery": recovery,
            "source_type": source_type,
        }

    for freeze_name in ("pp1_baseline_v1", "pp2_baseline_v1"):
        for path in sorted((processed / "frozen" / freeze_name).glob("**/*")):
            if path.is_file():
                add(
                    path,
                    "frozen_dataset",
                    "essential_to_retain_as_bytes",
                    "dataset_integrity|offline_demo|experiment_reproduction",
                    "preserved_in_git_and_verified_by_the_upstream_manifest",
                )

    tracked_feature_files = (
        "fr3_descriptor_schema.json",
        "fr3_descriptor_table.parquet",
        "fr3_record_map.csv",
        "fr3_embeddings_manifest.json",
        "fr3_embeddings_validation_report.json",
        "fr3_fusion_schema.json",
        "fr3_fusion_scalers.json",
        "fr3_fusion_validation_report.json",
        "fr3_feature_cache_manifest.json",
        "fr3_feature_cache_validation_report.json",
        "fr3_demo_output.json",
        "c3_similarity_ranking.csv",
    )
    for name in tracked_feature_files:
        add(
            processed / name,
            "feature_pipeline",
            "essential_to_retain_as_bytes",
            "offline_demo|feature_provenance|experiment_reproduction",
            "preserved_in_git; ignored arrays are regenerated by documented FR3 commands",
        )
    for path in sorted(processed.glob("fr3_*")):
        if path.is_file():
            add(
                path,
                "feature_pipeline",
                "essential_to_retain_as_bytes",
                "offline_demo|feature_provenance|experiment_reproduction",
                "preserved_in_git; ignored arrays are regenerated by documented FR3 commands",
            )

    for name in ("fr3_embeddings.npz", "fr3_fold0_scaled_features.npz"):
        add(
            interim / name,
            "offline_demo_cache",
            "essential_to_retain_as_bytes",
            "offline_demo|accepted_checkpoint_inference",
            "regenerable by the documented FR3 pipeline, but ESM extraction is required for embeddings",
        )
    for name in (
        "c3_candidate_embeddings.npz",
        "c3_positive_embeddings.npz",
        "fr3_fused_raw.npz",
        "fr3_fold1_scaled_features.npz",
        "fr3_fold2_scaled_features.npz",
        "fr3_fold3_scaled_features.npz",
        "fr3_fold4_scaled_features.npz",
    ):
        add(
            interim / name,
            "regenerable_cache",
            "regenerable_using_documented_pipeline",
            "full_feature_or_c3_reproduction",
            "regenerable from frozen inputs and recorded schemas using documented commands",
        )

    peptipedia = repo_root / "data/raw/c2_pu/Peptipedia/peptipedia.20240323.sql.gz"
    add(
        peptipedia,
        "external_source",
        "regenerable_using_documented_pipeline",
        "full_fr2_c2_reproduction",
        "recoverable from the recorded Zenodo DOI and verified by checksum",
        source_type="external_versioned_source",
    )

    summary_names = (
        "fr4_pn_baseline_fold0_summary.json",
        "fr4_nnpu_baseline_fold0_summary.json",
        "fr4_nnpu_corrective_fold0_summary.json",
        "fr4_two_step_pu_baseline_fold0_summary.json",
        "fr4_pu_bagging_baseline_fold0_summary.json",
        "fr4_nnpu_prior_sensitivity_pi0p05_fold0_summary.json",
        "fr4_nnpu_prior_sensitivity_pi0p20_fold0_summary.json",
    )
    for name in summary_names:
        summary_path = processed / name
        add(
            summary_path,
            "accepted_experiment_summary",
            "essential_to_retain_as_bytes",
            "experiment_provenance|preliminary_comparison",
            "preserved_in_git",
        )
        run_dir = Path(_load_json(summary_path)["run_dir"])
        for run_file in sorted(run_dir.glob("*")):
            if run_file.is_file():
                add(
                    run_file,
                    "accepted_experiment_run",
                    "essential_to_retain_as_bytes",
                    "checkpoint_loading|experiment_provenance",
                    "retraining is documented but does not substitute for retaining accepted checkpoint bytes",
                )

    curriculum_summary = processed / "fr4_curriculum_fold0_summary.json"
    add(
        curriculum_summary,
        "accepted_curriculum_summary",
        "essential_to_retain_as_bytes",
        "curriculum_provenance|preliminary_comparison",
        "preserved_in_git",
    )
    curriculum_run = Path(_load_json(curriculum_summary)["run_dir"])
    for run_file in sorted(curriculum_run.glob("**/*")):
        if run_file.is_file():
            add(
                run_file,
                "accepted_curriculum_run",
                "essential_to_retain_as_bytes",
                "checkpoint_loading|curriculum_provenance",
                "retraining is documented but does not substitute for retaining accepted checkpoint bytes",
            )

    result_patterns = (
        "fr4_*provenance.jsonl",
        "fr4_*learning_curve.svg",
        "fr4_baseline_*.json",
        "fr4_baseline_*.csv",
        "fr4_baseline_*.svg",
        "fr4_external_control_*.json",
        "fr4_external_control_*.csv",
        "fr4_curriculum_*.csv",
        "fr4_curriculum_*.svg",
        "fr4_pp1_matched_curriculum_fold0.csv",
        "fr4_pp1_matched_curriculum_fold0.svg",
        "fr4_nnpu_prior_sensitivity_*.json",
        "fr4_nnpu_prior_sensitivity_*.svg",
    )
    for pattern in result_patterns:
        for path in sorted(processed.glob(pattern)):
            add(
                path,
                "accepted_result",
                "essential_to_retain_as_bytes",
                "technical_handover|accepted_scientific_record",
                "preserved_in_git",
            )

    report_names = (
        "fr1_acceptance_report.md",
        "fr2_acceptance_report.md",
        "FR3_FEATURE_PIPELINE_DEMO.md",
        "FR4_BASELINE_EVALUATION_REPORT.md",
        "FR4_EXTERNAL_CONTROL_DIAGNOSTIC.md",
        "FR4_NNPU_PRIOR_SENSITIVITY_DIAGNOSTIC.md",
        "FR4_NNPU_CORRECTIVE_COMPARISON.md",
        "FR4_CURRICULUM_PROTOTYPE_REPORT.md",
        "FR4_PP1_PRE_FREEZE_METHOD_AUDIT.md",
    )
    for name in report_names:
        add(
            docs / name,
            "accepted_report",
            "essential_to_retain_as_bytes",
            "technical_handover|scientific_interpretation",
            "preserved_in_git",
        )
    return [specs[key] for key in sorted(specs)]


def _inventory_records(repo_root: Path, verified_backup_root: Path | None = None) -> list[dict]:
    records = []
    for spec in _accepted_artifact_specs(repo_root):
        path = repo_root / spec["path"]
        present = path.is_file()
        disposition = _git_disposition(spec["path"], repo_root)
        backup = "git" if disposition == "tracked" else "local_only_no_authorized_external_backup"
        if (
            verified_backup_root is not None
            and disposition == "ignored"
            and spec["retention"] == "essential_to_retain_as_bytes"
        ):
            backup = f"verified_external_data_copy:{Path(verified_backup_root).resolve()}"
        records.append(
            {
                **spec,
                "size_bytes": path.stat().st_size if present else "",
                "sha256": sha256_file(path) if present else "",
                "git_disposition": disposition,
                "available_locally": str(present).lower(),
                "preservation_location": backup,
            }
        )
    return records


def _package_versions() -> dict[str, str]:
    names = ("numpy", "pandas", "pyarrow", "torch", "scikit-learn", "pulearn", "joblib", "pytest")
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "NOT INSTALLED"
    return versions


def _portable_model_references(repo_root: Path) -> list[dict]:
    processed = repo_root / "data/processed/c2_pu"
    provenance = _load_json(processed / "fr4_baseline_model_provenance.json")
    result = []
    for model in provenance["models"]:
        result.append(
            {
                **{k: v for k, v in model.items() if k not in ("checkpoint_path", "summary_path")},
                "checkpoint_path": _repo_relative(Path(model["checkpoint_path"]), repo_root),
                "summary_path": _repo_relative(Path(model["summary_path"]), repo_root),
            }
        )
    return result


def create_release_files(
    repo_root: Path,
    implementation_revision: str,
    created_at: str,
    *,
    finalize: bool = False,
    backup_root: Path | None = None,
) -> dict:
    repo_root = Path(repo_root).resolve()
    datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    _git("cat-file", "-e", f"{implementation_revision}^{{commit}}", repo_root=repo_root)
    if finalize and backup_root is None:
        raise ValueError("Finalized freeze generation requires a verified backup root")
    resolved_backup_root = Path(backup_root).resolve() if backup_root is not None else None

    records = _inventory_records(repo_root, resolved_backup_root if finalize else None)
    missing = [record["path"] for record in records if record["available_locally"] != "true"]
    backup_verification = None
    if finalize:
        preservation_records = [
            record
            for record in records
            if record["git_disposition"] == "ignored"
            and record["retention"] == "essential_to_retain_as_bytes"
        ]
        backup_verification = _verify_directory_records(resolved_backup_root, preservation_records)
    inventory_path = repo_root / INVENTORY_RELATIVE_PATH
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0])
    with inventory_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    processed = repo_root / "data/processed/c2_pu"
    curriculum = _load_json(processed / "fr4_curriculum_fold0_summary.json")
    curriculum_stages = []
    for stage in curriculum["training"]["stages"]:
        curriculum_stages.append(
            {
                "stage": stage["stage"],
                "best_checkpoint": _repo_relative(Path(stage["best_checkpoint"]), repo_root),
                "best_checkpoint_sha256": stage["best_checkpoint_sha256"],
                "last_checkpoint": _repo_relative(Path(stage["last_checkpoint"]), repo_root),
                "last_checkpoint_sha256": stage["last_checkpoint_sha256"],
                "parent_checkpoint_sha256": stage["parent_checkpoint_sha256"],
            }
        )

    pp1_manifest = processed / "frozen/pp1_baseline_v1/MANIFEST.json"
    pp2_manifest = processed / "frozen/pp2_baseline_v1/MANIFEST.json"
    cache_manifest = processed / "fr3_feature_cache_manifest.json"
    pn_checkpoint = Path(_load_json(processed / "fr4_baseline_model_provenance.json")["models"][0]["checkpoint_path"])
    manifest = {
        "schema_version": "c2_pp1_freeze_manifest_v1",
        "release": {
            "id": RELEASE_ID,
            "component": "C2 / PU-AOP",
            "purpose": "PP1 technical demonstration and research baseline",
            "freeze_date": created_at[:10],
            "created_at": created_at,
            "status": "frozen_ready_with_limitations" if finalize else "prepared_awaiting_owner_commit_and_tag",
            "decision": "FROZEN — READY WITH LIMITATIONS" if finalize else "FREEZE INCOMPLETE",
            "methodological_audit_status": "READY WITH LIMITATIONS",
        },
        "source_control": {
            "branch_at_preparation": _git("branch", "--show-current", repo_root=repo_root).stdout.strip(),
            "verified_implementation_revision": implementation_revision,
            "revision_convention": (
                "This is the verified implementation parent revision. The release tag points to the later "
                "commit containing this manifest and the freeze documentation; resolving the tag identifies "
                "that release commit without self-referential manifest hashing."
            ),
            "release_tag": "c2-pp1-v1",
            "tag_status": "annotated_tag_targets_containing_release_commit" if finalize else "not_created_pending_owner_authorization",
            "preparation_initial_status": ["A  .idea/modules.xml"],
            "unrelated_worktree_policy": "pre-existing staged IDE file preserved and excluded from freeze changes",
        },
        "dependencies": {
            "python_requirement": ">=3.11",
            "recorded_environment": _package_versions(),
            "requirements_file": "requirements.txt",
            "frozen_datasets": [
                {"version": "pp1_baseline_v1", "manifest": _repo_relative(pp1_manifest, repo_root), "sha256": sha256_file(pp1_manifest)},
                {"version": "pp2_baseline_v1", "manifest": _repo_relative(pp2_manifest, repo_root), "sha256": sha256_file(pp2_manifest)},
            ],
            "fr3": {
                "descriptor_schema": "data/processed/c2_pu/fr3_descriptor_schema.json",
                "fusion_schema": "data/processed/c2_pu/fr3_fusion_schema.json",
                "fusion_scalers": "data/processed/c2_pu/fr3_fusion_scalers.json",
                "feature_cache_manifest": _repo_relative(cache_manifest, repo_root),
                "feature_cache_manifest_sha256": sha256_file(cache_manifest),
                "fold0_feature_cache": "data/interim/c2_pu/fr3_fold0_scaled_features.npz",
                "feature_dimension": 495,
            },
        },
        "accepted_models": _portable_model_references(repo_root),
        "accepted_curriculum": {
            "summary": "data/processed/c2_pu/fr4_curriculum_fold0_summary.json",
            "summary_sha256": sha256_file(processed / "fr4_curriculum_fold0_summary.json"),
            "matched_reference_alias": "weighted_c1_only_curriculum_reference",
            "stages": curriculum_stages,
        },
        "accepted_evidence": {
            "task_4_5_evaluation": "data/processed/c2_pu/fr4_baseline_evaluation_fold0.json",
            "external_control_diagnostic": "data/processed/c2_pu/fr4_external_control_diagnostic.json",
            "matched_curriculum_comparison": "data/processed/c2_pu/fr4_pp1_matched_curriculum_fold0.csv",
            "pre_freeze_audit": "src/plantaox/c2_pu/docs/FR4_PP1_PRE_FREEZE_METHOD_AUDIT.md",
        },
        "release_documents": {
            "freeze_report": {
                "path": "src/plantaox/c2_pu/docs/C2_PP1_FREEZE_REPORT.md",
                "sha256": sha256_file(repo_root / "src/plantaox/c2_pu/docs/C2_PP1_FREEZE_REPORT.md"),
            },
            "handover": {
                "path": "src/plantaox/c2_pu/docs/C2_PP1_HANDOVER.md",
                "sha256": sha256_file(repo_root / "src/plantaox/c2_pu/docs/C2_PP1_HANDOVER.md"),
            },
            "read_only_verifier": "src/plantaox/c2_pu/pp1_freeze.py",
        },
        "artifact_inventory": {
            "path": INVENTORY_RELATIVE_PATH.as_posix(),
            "sha256": sha256_file(inventory_path),
            "record_count": len(records),
            "missing_count": len(missing),
            "missing_paths": missing,
            "git_disposition_counts": dict(Counter(r["git_disposition"] for r in records)),
            "retention_counts": dict(Counter(r["retention"] for r in records)),
            "non_git_backup_status": (
                "56 essential ignored artifacts independently verified in the owner-supplied external data copy"
                if finalize
                else "local_only; no external backup destination was authorized for this task"
            ),
        },
        "preservation": (
            {
                "status": "PASS",
                "method": "existing owner-created data-directory copy; read-only size and SHA-256 verification",
                "nonportable_backup_root": str(resolved_backup_root),
                "backup_layout": backup_verification["backup_layout"],
                "artifact_count_expected": backup_verification["artifact_count_expected"],
                "artifact_count_verified": backup_verification["artifact_count_verified"],
                "verified_bytes": backup_verification["verified_bytes"],
                "failures": backup_verification["failures"],
                "verified_at": backup_verification["verified_at"],
            }
            if finalize
            else {
                "status": "PENDING",
                "method": "no authorized external backup destination",
            }
        ),
        "offline_smoke": {
            "fold_id": 0,
            "feature_cache_manifest": "data/processed/c2_pu/fr3_feature_cache_manifest.json",
            "fusion_scalers": "data/processed/c2_pu/fr3_fusion_scalers.json",
            "c3_ranking": "data/processed/c2_pu/c3_similarity_ranking.csv",
            "baseline_checkpoint": _repo_relative(pn_checkpoint, repo_root),
            "curriculum_stage_c1_best": curriculum_stages[0]["best_checkpoint"],
            "curriculum_stage_c3_best": curriculum_stages[2]["best_checkpoint"],
            "expected_shape": [8, 1],
            "command": "python -m plantaox.c2_pu.pp1_freeze verify --manifest data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json",
        },
        "validation_status": {
            "technical": "accepted and reproducible in the current local environment",
            "scientific": "reliable antioxidant-activity discrimination not established",
            "supervisor_approval": "pending where recorded in FR1/FR2 acceptance reports and IMPLEMENTATION_STATUS.md",
        },
        "known_limitations": [
            "Task 4.5 assay-supported MCC values are negative and AUROC values are below 0.5 for all five configurations.",
            "The external inactive-control set contains only 38 assay-specific peptides and two cross-database annotation conflicts.",
            "E2 evidence is provisional and pi=0.10 is an assumed class prior.",
            "Positive and unlabeled pools have source and descriptor distribution differences that may support shortcuts.",
            "Curriculum checkpoint selection uses a C1-based surrogate even for C2 and C3 training stages.",
            "Evaluation is fold-0 only and model scores are not calibrated biological probabilities.",
            (
                "Git-ignored checkpoint and cache bytes require both the verified external data copy and Git release references; the tag alone does not contain these bytes."
                if finalize
                else "Git-ignored checkpoint and cache bytes are currently local-only and are not made portable by the proposed Git tag."
            ),
        ],
        "pending_decisions": [
            "Supervisor confirmation of the SwissProt/UniProtKB-reviewed C1 source interpretation.",
            "Supervisor review of the 179 positive/inactive label conflicts and the provisional E2 policy.",
            "Project-owner confirmation of retaining and flagging the two BIOPEP-UWM/external-control conflicts.",
            *([] if finalize else ["Owner authorization for the freeze commit, c2-pp1-v1 tag, and an external artifact-backup destination."]),
        ],
        "verification_instructions": [
            "Use .venv/Scripts/python.exe (Python 3.11.14) and set PYTHONPATH=src.",
            "Run the offline_smoke.command from the repository root.",
            "Run pytest tests/c2_pu/test_pp1_freeze.py -q for focused regression coverage.",
        ],
    }
    manifest_path = repo_root / MANIFEST_RELATIVE_PATH
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def verify_release(repo_root: Path, manifest_path: Path) -> dict:
    repo_root = Path(repo_root).resolve()
    manifest_path = Path(manifest_path)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    manifest = _load_json(manifest_path)
    if manifest["release"]["id"] != RELEASE_ID:
        raise ValueError(f"Unexpected release id: {manifest['release']['id']}")

    inventory_meta = manifest["artifact_inventory"]
    inventory_path = repo_root / inventory_meta["path"]
    if sha256_file(inventory_path) != inventory_meta["sha256"]:
        raise ValueError("Artifact inventory SHA-256 does not match the release manifest")
    with inventory_path.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    failures = []
    for record in records:
        path = repo_root / record["path"]
        if not path.is_file():
            failures.append(f"missing: {record['path']}")
            continue
        if path.stat().st_size != int(record["size_bytes"]):
            failures.append(f"size mismatch: {record['path']}")
        if sha256_file(path) != record["sha256"]:
            failures.append(f"sha256 mismatch: {record['path']}")
        if _git_disposition(record["path"], repo_root) != record["git_disposition"]:
            failures.append(f"git disposition mismatch: {record['path']}")
    if failures:
        raise ValueError("Release inventory verification failed: " + "; ".join(failures[:10]))

    from plantaox.c2_pu.common.feature_cache import (
        get_c3_fold_challenge_rows,
        get_held_out_rows,
        get_pool_rows,
        load_fold_feature_cache,
    )
    from plantaox.c2_pu.curation.freeze import verify_frozen_baseline

    frozen_results = {}
    for dataset in manifest["dependencies"]["frozen_datasets"]:
        if sha256_file(repo_root / dataset["manifest"]) != dataset["sha256"]:
            raise ValueError(f"Frozen manifest hash mismatch for {dataset['version']}")
        freeze_dir = (repo_root / dataset["manifest"]).parent
        result = verify_frozen_baseline(freeze_dir)
        frozen_results[dataset["version"]] = {"checked": len(result), "all_valid": all(result.values())}
        if not all(result.values()):
            raise ValueError(f"Frozen dataset verification failed for {dataset['version']}")

    cache_manifest = _load_json(repo_root / manifest["offline_smoke"]["feature_cache_manifest"])
    verified_caches = {}
    loaded_caches = {}
    for fold_id, fold_entry in sorted(cache_manifest["folds"].items()):
        cache_path = repo_root / f"data/interim/c2_pu/fr3_fold{fold_id}_scaled_features.npz"
        fold_cache = load_fold_feature_cache(cache_path, fold_entry)
        loaded_caches[fold_id] = fold_cache
        verified_caches[fold_id] = {
            "shape": list(fold_cache["features"].shape),
            "dtype": str(fold_cache["features"].dtype),
            "sha256": fold_entry["cache_sha256"],
        }
    cache = loaded_caches["0"]
    embeddings_manifest = _load_json(repo_root / "data/processed/c2_pu/fr3_embeddings_manifest.json")
    if sha256_file(repo_root / "data/interim/c2_pu/fr3_embeddings.npz") != embeddings_manifest["embeddings_cache_sha256"]:
        raise ValueError("FR3 embedding-cache hash does not match its accepted manifest")
    c3_ids, _, _ = get_c3_fold_challenge_rows(
        cache, repo_root / manifest["offline_smoke"]["c3_ranking"], 0
    )
    scalers = _load_json(repo_root / manifest["offline_smoke"]["fusion_scalers"])
    scaler = scalers["0"]
    _, held_out_features = get_held_out_rows(cache, scaler["held_out_peptide_ids"][:8])
    external_ids, _ = get_pool_rows(cache, "external_control")
    forbidden = set(scaler["training_peptide_ids"]) | set(scaler["held_out_peptide_ids"])
    external_overlap = set(external_ids.tolist()) & forbidden
    if external_overlap:
        raise ValueError(f"External controls overlap positive training/held-out IDs: {sorted(external_overlap)[:5]}")
    if len(c3_ids) != 2000 or int((cache["pools"] == "C3").sum()) != 2325:
        raise ValueError("Fold-0 C3 selection no longer satisfies the 2,000-of-2,325 contract")

    for model in manifest["accepted_models"]:
        if sha256_file(repo_root / model["checkpoint_path"]) != model["checkpoint_sha256"]:
            raise ValueError(f"Accepted checkpoint hash mismatch for {model['model_id']}")
    for stage in manifest["accepted_curriculum"]["stages"]:
        for checkpoint_kind in ("best", "last"):
            path_key = f"{checkpoint_kind}_checkpoint"
            hash_key = f"{checkpoint_kind}_checkpoint_sha256"
            if sha256_file(repo_root / stage[path_key]) != stage[hash_key]:
                raise ValueError(f"Curriculum {stage['stage']} {checkpoint_kind} checkpoint hash mismatch")
    for release_document in ("freeze_report", "handover"):
        item = manifest["release_documents"][release_document]
        if sha256_file(repo_root / item["path"]) != item["sha256"]:
            raise ValueError(f"Release-document hash mismatch for {release_document}")

    import numpy as np
    import torch

    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import load_checkpoint

    tensor = torch.as_tensor(held_out_features, dtype=torch.float32)
    checkpoint_results = {}
    for label in ("baseline_checkpoint", "curriculum_stage_c1_best", "curriculum_stage_c3_best"):
        checkpoint_path = repo_root / manifest["offline_smoke"][label]
        model = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(128, 64), activation="relu"))
        metadata = load_checkpoint(checkpoint_path, model)
        scores = model.predict_proba(tensor).detach().cpu().numpy()
        expected_shape = tuple(manifest["offline_smoke"]["expected_shape"])
        if scores.shape != expected_shape or not np.isfinite(scores).all() or not ((0 <= scores) & (scores <= 1)).all():
            raise ValueError(f"Invalid inference output for {label}: shape={scores.shape}")
        checkpoint_results[label] = {
            "path": manifest["offline_smoke"][label],
            "epoch": metadata["epoch"],
            "shape": list(scores.shape),
            "finite_and_bounded": True,
        }

    return {
        "release_id": RELEASE_ID,
        "manifest": _repo_relative(manifest_path, repo_root),
        "inventory_records_verified": len(records),
        "inventory_missing": 0,
        "frozen_datasets": frozen_results,
        "fr3_feature_caches": verified_caches,
        "fr3_embedding_cache": {
            "sha256": embeddings_manifest["embeddings_cache_sha256"],
            "total_embeddings": embeddings_manifest["total_embeddings"],
            "embedding_dim": embeddings_manifest["embedding_dim"],
        },
        "fold0_cache": verified_caches["0"],
        "c3_contract": {"fold0_selected": len(c3_ids), "union_in_cache": int((cache["pools"] == "C3").sum())},
        "external_control_overlap_with_positive_partitions": 0,
        "checkpoint_inference": checkpoint_results,
        "status": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="Write the deterministic PP1 inventory and release manifest")
    create.add_argument("--implementation-revision", required=True)
    create.add_argument("--created-at", required=True, help="ISO-8601 release preparation timestamp")
    create.add_argument("--finalize", action="store_true", help="Write the owner-authorized final freeze state")
    create.add_argument("--backup-root", type=Path, help="Existing owner-supplied backup data directory")
    create.add_argument("--repo-root", type=Path, default=Path.cwd())
    verify = subparsers.add_parser("verify", help="Read-only artifact and offline inference verification")
    verify.add_argument("--manifest", type=Path, default=MANIFEST_RELATIVE_PATH)
    verify.add_argument("--repo-root", type=Path, default=Path.cwd())
    preserve = subparsers.add_parser(
        "preserve", help="Create and verify the 56-artifact external preservation package"
    )
    preserve.add_argument("--manifest", type=Path, default=MANIFEST_RELATIVE_PATH)
    preserve.add_argument("--destination", type=Path, required=True)
    preserve.add_argument("--repo-root", type=Path, default=Path.cwd())
    verify_backup = subparsers.add_parser(
        "verify-backup", help="Independently verify an external preservation package"
    )
    verify_backup.add_argument("--manifest", type=Path, default=MANIFEST_RELATIVE_PATH)
    verify_backup.add_argument("--archive", type=Path, required=True)
    verify_backup.add_argument("--verification-record", type=Path, required=True)
    verify_backup.add_argument("--repo-root", type=Path, default=Path.cwd())
    verify_directory = subparsers.add_parser(
        "verify-backup-directory", help="Verify an existing copied data directory without modifying it"
    )
    verify_directory.add_argument("--manifest", type=Path, default=MANIFEST_RELATIVE_PATH)
    verify_directory.add_argument("--backup-root", type=Path, required=True)
    verify_directory.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.command == "create":
        result = create_release_files(
            args.repo_root,
            args.implementation_revision,
            args.created_at,
            finalize=args.finalize,
            backup_root=args.backup_root,
        )
    elif args.command == "verify":
        result = verify_release(args.repo_root, args.manifest)
    elif args.command == "preserve":
        result = create_preservation_package(args.repo_root, args.manifest, args.destination)
    elif args.command == "verify-backup":
        result = verify_preservation_package(
            args.repo_root, args.manifest, args.archive, args.verification_record
        )
    else:
        result = verify_preservation_directory(
            args.repo_root, args.manifest, args.backup_root
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
