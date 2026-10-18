"""Run Component 4 candidate generation: download, digest, or all."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

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


def main(argv: list[str] | None = None) -> None:
    parser_cli = argparse.ArgumentParser(description=__doc__)
    parser_cli.add_argument("stage", choices=("download", "digest", "all"))
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


if __name__ == "__main__":
    main()
