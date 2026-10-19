"""Run Component 4 candidate generation and downstream screening stages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml
import numpy as np

from .embed_import import import_embeddings
from .cloud import build_reference_meta
from .ad import assign_tiers, write_ad_diagnostics
from .signals import generate_and_validate_mock_signals, validate_and_join_signals
from .score import score_candidates
from .cards import make_cards
from .dashboard import build_summary, write_dashboard

from .dedup import deduplicate, deduplicate_by_plant
from .descriptors import add_descriptors
from .digest import download_proteomes, digest_protein, load_proteins
from .filters import filter_fragments

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def _write_fasta(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(f">{row['peptide_id']}\n{row['sequence']}\n")


def run_digest(config: dict, raw_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    all_filtered, funnel = [], []
    exclusions_by_plant = {}
    for plant in config["plants"]:
        path = raw_dir / "proteomes" / f"{plant}.fasta"
        proteins, exclusions = load_proteins(path, plant)
        exclusions_by_plant[plant] = exclusions
        fragments = [fragment for protein in proteins
                     for fragment in digest_protein(protein, int(config.get("missed_cleavages", 0)))]
        retained, counts = filter_fragments(
            fragments, int(config["length"]["min"]), int(config["length"]["max"]),
            int(config["min_unique_amino_acids"]))
        all_filtered.extend(retained)
        funnel.append({"plant": plant, "proteins": len(proteins), "protein_exclusions": len(exclusions),
                       **counts})
    candidates, membership = deduplicate(all_filtered)
    # Per-plant tables retain all provenance for that plant and sequence.
    for plant in config["plants"]:
        per_plant = deduplicate_by_plant(all_filtered, plant)
        pd.DataFrame(add_descriptors(per_plant)).to_parquet(out_dir / f"candidates_{plant}.parquet", index=False)
    enriched = add_descriptors(candidates)
    pd.DataFrame(enriched).to_parquet(out_dir / "candidates.parquet", index=False)
    pd.DataFrame(membership, columns=["peptide_id", "sequence", "plant"]).to_parquet(
        out_dir / "plant_membership.parquet", index=False)
    _write_fasta(out_dir / "candidates.fasta", candidates)

    membership_counts = pd.DataFrame(membership).groupby("plant").size().to_dict() if membership else {}
    for row in funnel:
        row["deduplicated"] = int(membership_counts.get(row["plant"], 0))
    _write_csv(out_dir / "funnel_summary.csv", funnel)
    exclusion_rows = [item for group in exclusions_by_plant.values() for item in group]
    _write_csv(raw_dir / "metadata" / "c4_protein_exclusions.csv", exclusion_rows)
    # Record the exact-match policy and short-peptide equivalence without invoking CD-HIT.
    summary = {"funnel": funnel}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(pd.DataFrame(funnel).to_string(index=False))
    return summary


def run_embed_import(out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray, dict]:
    return import_embeddings(out_dir / "candidates.parquet", out_dir / "embeddings",
                             manifest_copy=out_dir / "c4_embedding_manifest.json")


def run_cloud(out_dir: Path) -> pd.DataFrame:
    embeddings = out_dir / "embeddings"
    meta = build_reference_meta(embeddings / "ref_cloud_sequences.csv", out_dir / "ref_cloud_meta.csv")
    return meta


def run_ad(out_dir: Path, config: dict) -> pd.DataFrame:
    candidates, index, matrix, cloud_meta, cloud, _ = run_embed_import(out_dir)
    cloud_meta = run_cloud(out_dir)
    memberships = pd.read_parquet(out_dir / "plant_membership.parquet")
    tiers, params, cloud_distances = assign_tiers(candidates, index, matrix, cloud,
        float(config.get("sd_multiplier", 1.0)), "mock_cloud")
    tiers["cloud_source"] = "mock_cloud"
    tiers.to_parquet(out_dir / "c4_ad_tiers.parquet", index=False)
    (out_dir / "ad_params.json").write_text(json.dumps(params, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_ad_diagnostics(tiers, memberships, candidates, cloud_distances, params, out_dir / "diagnostics",
                         cloud_embeddings=cloud, candidate_embeddings=matrix, embedding_index=index)
    return tiers


def run_signals(out_dir: Path, config: dict) -> dict:
    tiers = pd.read_parquet(out_dir / "c4_ad_tiers.parquet")
    embedded = tiers.loc[tiers.embedded.astype(bool), ["sequence", "d_norm", "tier"]].copy()
    signal_dir = out_dir / "signals"
    tier_input = signal_dir / "tier_candidates.parquet"
    signal_dir.mkdir(parents=True, exist_ok=True)
    embedded.to_parquet(tier_input, index=False)
    generate_and_validate_mock_signals(tier_input, signal_dir, int(config.get("seed", 42)), 10)
    manifest_path = signal_dir / "MOCK_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"] = "mock"
    manifest["cloud_source"] = "mock_cloud"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def run_score(out_dir: Path, config: dict) -> pd.DataFrame:
    tiers = pd.read_parquet(out_dir / "c4_ad_tiers.parquet")
    embedded = tiers.loc[tiers.embedded.astype(bool)].copy()
    joined, bcs = validate_and_join_signals(embedded, out_dir / "signals")
    (out_dir / "signals" / "c3_bcs.json").write_text(json.dumps(bcs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    candidates = pd.read_parquet(out_dir / "candidates.parquet")
    memberships = pd.read_parquet(out_dir / "plant_membership.parquet")
    ranked = score_candidates(joined, memberships, candidates, config)
    ranked.to_parquet(out_dir / "c4_ranked_candidates.parquet", index=False)
    return ranked


def run_cards(out_dir: Path, config: dict) -> dict:
    ranked = pd.read_parquet(out_dir / "c4_ranked_candidates.parquet")
    mock_manifest = json.loads((out_dir / "signals" / "MOCK_MANIFEST.json").read_text(encoding="utf-8"))
    bcs = json.loads((out_dir / "signals" / "c3_bcs.json").read_text(encoding="utf-8"))
    return make_cards(ranked, config, mock_manifest, bcs, out_dir / "cards.json")


def run_dashboard(out_dir: Path, cards: dict) -> dict:
    tiers = pd.read_parquet(out_dir / "c4_ad_tiers.parquet")
    memberships = pd.read_parquet(out_dir / "plant_membership.parquet")
    tiers = tiers.merge(memberships[["peptide_id", "plant"]], on="peptide_id", how="left", validate="one_to_many")
    candidates = pd.read_parquet(out_dir / "candidates.parquet")
    cloud_meta = pd.read_csv(out_dir / "ref_cloud_meta.csv")
    params = json.loads((out_dir / "ad_params.json").read_text(encoding="utf-8"))
    funnel_path = out_dir / "funnel_summary.csv"
    signal_sources = {"SIM_C1": "mock", "PROB_C2": "mock", "BCS": "mock", "cloud": "mock_cloud"}
    summary = build_summary(funnel_path, tiers, candidates, cloud_meta, params, signal_sources, out_dir / "summary.json")
    write_dashboard(summary, cards, out_dir / "c4_dashboard.html")
    return summary


def write_output_manifest(out_dir: Path) -> Path:
    """Checksum generated outputs without copying or hashing the external embedding handoff."""
    manifest_path = out_dir / "c4_output_manifest.json"
    entries = []
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or path == manifest_path or "embeddings" in path.relative_to(out_dir).parts:
            continue
        if path.suffix in {".npy", ".pt", ".pth"}:
            continue
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        entries.append({"path": path.relative_to(out_dir).as_posix(), "size_bytes": path.stat().st_size,
                        "sha256": digest.hexdigest()})
    manifest_path.write_text(json.dumps({"status": "MOCK / PROVISIONAL", "files": entries},
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def run_all_downstream(out_dir: Path, config: dict) -> None:
    # A missing handoff intentionally stops this production path with the exact missing filenames.
    run_embed_import(out_dir)
    run_cloud(out_dir)
    run_ad(out_dir, config)
    run_signals(out_dir, config)
    run_score(out_dir, config)
    cards = run_cards(out_dir, config)
    run_dashboard(out_dir, cards)
    write_output_manifest(out_dir)


def main(argv: list[str] | None = None) -> None:
    parser_cli = argparse.ArgumentParser(description=__doc__)
    parser_cli.add_argument("stage", choices=("download", "digest", "all", "embed-import", "cloud", "ad", "signals", "score", "cards", "dashboard"))
    parser_cli.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser_cli.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw" / "c4_screen")
    parser_cli.add_argument("--out-dir", type=Path, default=ROOT / "data" / "interim" / "c4_screen")
    args = parser_cli.parse_args(argv)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    raw_dir = args.raw_dir
    if args.stage in {"download", "all"}:
        records = download_proteomes(raw_dir, config["plants"])
        print(pd.DataFrame(records)[["plant", "protein_count_downloaded", "protein_count_retained",
                                     "protein_count_excluded"]].to_string(index=False))
    if args.stage in {"digest", "all"}:
        run_digest(config, raw_dir, args.out_dir)
    if args.stage == "all":
        run_all_downstream(args.out_dir, config)
    elif args.stage == "embed-import":
        run_embed_import(args.out_dir)
    elif args.stage == "cloud":
        run_cloud(args.out_dir)
    elif args.stage == "ad":
        run_ad(args.out_dir, config)
    elif args.stage == "signals":
        run_signals(args.out_dir, config)
    elif args.stage == "score":
        run_score(args.out_dir, config)
    elif args.stage == "cards":
        run_cards(args.out_dir, config)
    elif args.stage == "dashboard":
        cards = json.loads((args.out_dir / "cards.json").read_text(encoding="utf-8"))
        run_dashboard(args.out_dir, cards)


if __name__ == "__main__":
    main()
