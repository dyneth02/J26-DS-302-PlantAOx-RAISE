"""Stable exact sequence deduplication with complete parent provenance."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict


def peptide_id(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def deduplicate(fragments: list[dict]) -> tuple[list[dict], list[dict]]:
    """Deduplicate across plants and retain a separate plant membership table."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in fragments:
        grouped[row["sequence"]].append(row)
    candidates, memberships = [], []
    for sequence in sorted(grouped):
        parents = sorted({(r["plant"], r["parent_accession"], int(r["start"]), int(r["end"]), r["enzyme_path"])
                          for r in grouped[sequence]})
        plants = sorted({x[0] for x in parents})
        candidates.append({"sequence": sequence, "peptide_id": peptide_id(sequence),
                           "length": len(sequence), "n_parents": len(parents),
                           "provenance": json.dumps([
                               {"plant": p, "parent_accession": a, "start": s, "end": e, "enzyme_path": path}
                               for p, a, s, e, path in parents], sort_keys=True, separators=(",", ":"))})
        memberships.extend({"peptide_id": peptide_id(sequence), "sequence": sequence, "plant": plant}
                           for plant in plants)
    return candidates, sorted(memberships, key=lambda r: (r["plant"], r["sequence"]))


def deduplicate_by_plant(fragments: list[dict], plant: str) -> list[dict]:
    """Per-plant unique sequence records; provenance is still aggregated globally."""
    return deduplicate([r for r in fragments if r["plant"] == plant])[0]
