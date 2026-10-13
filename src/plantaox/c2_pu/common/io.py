"""FASTA/CSV/parquet I/O helpers and provenance logging for Component 02."""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path


def read_fasta(path: str | Path) -> list[tuple[str, str]]:
    """Return a list of (header_without_>, sequence) tuples, in file order."""
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n\r")
            if line.startswith(">"):
                if header is not None:
                    records.append((header, "".join(chunks)))
                header = line[1:]
                chunks = []
            else:
                chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def write_fasta(path: str | Path, records: list[tuple[str, str]]) -> None:
    """Write (header, sequence) tuples as a FASTA file."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for header, sequence in records:
            handle.write(f">{header}\n{sequence}\n")


def append_provenance_log(path: str | Path, entry: dict) -> None:
    """Append one timestamped JSON-lines provenance record."""
    entry = {"timestamp": _dt.datetime.now().isoformat(), **entry}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
