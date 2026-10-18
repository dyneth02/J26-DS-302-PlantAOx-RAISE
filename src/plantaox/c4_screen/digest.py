"""Reviewed proteome ingestion and sequential in-silico pepsin/trypsin digestion."""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

from Bio import SeqIO
from pyteomics import parser

STANDARD_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")
UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/stream?compressed=false&format=fasta&query=%28taxonomy_id%3A{taxid}%29+AND+%28reviewed%3Atrue%29"
RULE_NAMES = {"pepsin": "pepsin ph1.3", "trypsin": "trypsin"}
LOCAL_VERIFIED_INPUTS = {
    "soybean": "uniprot_reviewed_3847_glycine_max.fasta",
    "rice": "uniprot_reviewed_39947_oryza_sativa_japonica.fasta",
    "rapeseed": "uniprot_reviewed_3708_brassica_napus.fasta",
    "olive": "uniprot_reviewed_4146_olea_europaea.fasta",
}
LOCAL_VERIFIED_SHA256 = {
    "soybean": "ad2c96c599cbd327a957bcb86ace1c678a7f2ebc1d339aceaa51fb79d48c24a7",
    "rice": "d2d3939436dbd26cc328cf45145263ab67551f4d63279db624477fb3a0a55ffb",
    "rapeseed": "7c98d4d0cd93fbc25a75f8b76b8a43e6fe1bcafa7443cff8c2f57a4bc13160ef",
    "olive": "ecf93a4676a8ae137228b22c4d423211e79325e6acb5c629ca0770e6d1407456",
}


def _fasta_records(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        yield from SeqIO.parse(handle, "fasta")


def download_proteomes(raw_dir: str | Path, plants: dict) -> list[dict]:
    """Fetch reviewed UniProt records and emit registry plus exclusion ledger."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir = raw_dir / "metadata"
    proteome_dir = raw_dir / "proteomes"
    downloads_dir = proteome_dir / "source_downloads"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    proteome_dir.mkdir(parents=True, exist_ok=True)
    prior_registry = {}
    prior_path = metadata_dir / "c4_data_registry.csv"
    if prior_path.exists():
        with prior_path.open("r", encoding="utf-8", newline="") as handle:
            prior_registry = {row.get("plant", ""): row for row in csv.DictReader(handle)}
    registry, exclusions = [], []
    for plant, spec in plants.items():
        url = UNIPROT_URL.format(taxid=spec["taxonomy_id"])
        path = proteome_dir / f"{plant}.fasta"
        release = prior_registry.get(plant, {}).get("uniprot_release", "unknown")
        access_date = prior_registry.get(plant, {}).get("access_date", date.today().isoformat())
        if not path.exists():
            verified_source = downloads_dir / LOCAL_VERIFIED_INPUTS[plant]
            if verified_source.exists():
                source_hash = hashlib.sha256(verified_source.read_bytes()).hexdigest()
                if source_hash != LOCAL_VERIFIED_SHA256[plant]:
                    raise ValueError(f"Cached {plant} FASTA does not match its recorded reviewed-query checksum")
                shutil.copyfile(verified_source, path)
                release = "2026_03 (previously recorded UniProt response header)"
                access_date = "2026-10-19"
            else:
                request = Request(url, headers={"User-Agent": "PlantAOx-RAISE-C4/1.0"})
                with urlopen(request, timeout=120) as response, path.open("wb") as output:
                    output.write(response.read())
                    release = response.headers.get("X-UniProt-Release", "not reported")
                    access_date = date.today().isoformat()
        records = list(_fasta_records(path))
        kept = []
        for rec in records:
            seq = str(rec.seq).upper()
            invalid = "".join(sorted(set(seq) - STANDARD_AA))
            reason = "shorter_than_50_aa" if len(seq) < 50 else ("non_standard_residues" if invalid else "")
            if reason:
                exclusions.append({"plant": plant, "accession": _accession(rec), "length": len(seq),
                                   "exclusion_reason": reason, "invalid_residues": invalid})
            else:
                kept.append(rec)
        registry.append({"plant": plant, "taxonomy_id": spec["taxonomy_id"], "url": url,
                         "access_date": access_date, "file_size_bytes": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "protein_count_downloaded": len(records), "protein_count_retained": len(kept),
                         "protein_count_excluded": len(records) - len(kept),
                         "uniprot_release": release})
    _write_csv(metadata_dir / "c4_data_registry.csv", registry)
    _write_csv(metadata_dir / "c4_protein_exclusions.csv", exclusions)
    return registry


def _accession(record) -> str:
    match = re.match(r"(?:sp|tr)\|([^|]+)\|", record.id)
    return match.group(1) if match else record.id


def _write_fasta(records: Iterable, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        SeqIO.write(records, handle, "fasta")


def _write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def load_proteins(path: str | Path, plant: str) -> tuple[list[dict], list[dict]]:
    """Parse existing FASTA and exclude short or non-standard proteins."""
    proteins, exclusions = [], []
    for rec in _fasta_records(Path(path)):
        seq = str(rec.seq).upper()
        invalid = "".join(sorted(set(seq) - STANDARD_AA))
        reason = "shorter_than_50_aa" if len(seq) < 50 else ("non_standard_residues" if invalid else "")
        row = {"plant": plant, "accession": _accession(rec), "sequence": seq}
        if reason:
            exclusions.append({"plant": plant, "accession": row["accession"], "length": len(seq),
                               "exclusion_reason": reason, "invalid_residues": invalid})
        else:
            proteins.append(row)
    return proteins, exclusions


def _cleave_with_positions(sequence: str, rule: str, missed_cleavages: int, offset: int):
    """Use pyteomics' returned zero-based start offsets, including repeats safely."""
    for local_start, peptide in parser.icleave(
        sequence, rule, missed_cleavages=missed_cleavages, regex=True
    ):
        local_end = local_start + len(peptide)
        yield peptide, offset + local_start, offset + local_end - 1


def digest_protein(protein: dict, missed_cleavages: int = 0) -> list[dict]:
    """Digest each pepsin fragment with trypsin; coordinates are 1-based inclusive."""
    pepsin_rule = parser.expasy_rules[RULE_NAMES["pepsin"]]
    trypsin_rule = parser.expasy_rules[RULE_NAMES["trypsin"]]
    result = []
    for first, pstart, pend in _cleave_with_positions(protein["sequence"], pepsin_rule, missed_cleavages, 0):
        for peptide, tstart, tend in _cleave_with_positions(first, trypsin_rule, missed_cleavages, pstart):
            result.append({"plant": protein["plant"], "sequence": peptide,
                           "parent_accession": protein["accession"], "start": tstart + 1,
                           "end": tend + 1, "enzyme_path": "pepsin_ph1.3>trypsin"})
    return result
