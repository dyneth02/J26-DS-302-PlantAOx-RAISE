"""FR1 (Bucket 1.5) — exact-duplicate removal and CD-HIT 90% identity clustering.

CD-HIT is a Linux binary, invoked here via WSL (no native Windows build). The
positive pool is dominated by very short peptides (median ~6 AA; see
IMPLEMENTATION_STATUS.md), which breaks CD-HIT's officially recommended word
length for 90% identity (-n 5): a 5-mer index cannot be built for sequences
shorter than 5 residues. A shorter word length only costs CD-HIT some
clustering speed/sensitivity -- it does NOT relax the identity threshold
itself -- so this module deliberately uses -n 2 (CD-HIT's minimum) to avoid
silently excluding ~35% of the pool from clustering.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

CDHIT_IDENTITY = 0.90
CDHIT_WORD_LENGTH = 2  # see module docstring -- deliberately NOT the "recommended" 5
CDHIT_THROWAWAY_LENGTH = 2  # must be < word length; smallest sequence we accept is 3 AA

_CLSTR_HEADER_RE = re.compile(r"^>Cluster (\d+)$")
_CLSTR_MEMBER_RE = re.compile(
    r"^(\d+)\t(\d+)aa, >(\S+?)\.\.\. (\*|at ([\d.]+)%)$"
)


class CDHitNotAvailableError(RuntimeError):
    """Raised when cd-hit cannot be invoked (e.g. WSL/apt setup not done yet)."""


def to_wsl_path(windows_path: Path) -> str:
    """Translate an absolute Windows path to its /mnt/<drive>/... WSL path."""
    resolved = Path(windows_path).resolve()
    drive_letter = resolved.drive.rstrip(":").lower()
    rest = str(resolved)[len(resolved.drive) + 1 :].replace("\\", "/")
    return f"/mnt/{drive_letter}/{rest}"


def check_cdhit_available(wsl_distro: str = "Ubuntu") -> bool:
    result = subprocess.run(
        ["wsl.exe", "-d", wsl_distro, "-e", "bash", "-lc", "command -v cd-hit"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def run_cdhit(
    input_fasta: Path,
    output_prefix: Path,
    identity: float = CDHIT_IDENTITY,
    word_length: int = CDHIT_WORD_LENGTH,
    throwaway_length: int = CDHIT_THROWAWAY_LENGTH,
    wsl_distro: str = "Ubuntu",
) -> tuple[Path, Path]:
    """Run CD-HIT (inside WSL) on ``input_fasta``.

    Returns (representative_fasta_path, clstr_path), both as native Windows
    Path objects pointing at the same files CD-HIT wrote inside WSL (paths
    under the repo, which WSL sees via /mnt/<drive>/...).
    """
    if not check_cdhit_available(wsl_distro):
        raise CDHitNotAvailableError(
            f"cd-hit not found in WSL distro '{wsl_distro}'. Install it with: "
            f"wsl -d {wsl_distro} -e sudo apt install -y cd-hit"
        )

    wsl_in = to_wsl_path(input_fasta)
    wsl_out = to_wsl_path(output_prefix)
    cmd = [
        "wsl.exe",
        "-d",
        wsl_distro,
        "-e",
        "cd-hit",
        "-i",
        wsl_in,
        "-o",
        wsl_out,
        "-c",
        str(identity),
        "-n",
        str(word_length),
        "-l",
        str(throwaway_length),
        "-d",
        "0",  # keep full FASTA headers (untruncated) in the .clstr file
        "-M",
        "0",  # unlimited memory
        "-T",
        "0",  # use all available threads
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"cd-hit failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )

    clstr_path = Path(str(output_prefix) + ".clstr")
    if not output_prefix.exists() or not clstr_path.exists():
        raise RuntimeError(
            "cd-hit reported success but expected output files are missing:\n"
            f"  representatives: {output_prefix} (exists={output_prefix.exists()})\n"
            f"  clusters:        {clstr_path} (exists={clstr_path.exists()})\n"
            f"stdout:\n{result.stdout}"
        )
    return output_prefix, clstr_path


@dataclass(frozen=True)
class ClusterMember:
    cluster_id: int
    peptide_id: str
    length_aa: int
    is_representative: bool
    pct_identity_to_representative: float | None  # None for the representative itself


def parse_cdhit_clusters(clstr_path: Path) -> list[ClusterMember]:
    """Parse a CD-HIT .clstr file into a flat list of ClusterMember rows."""
    members: list[ClusterMember] = []
    current_cluster: int | None = None
    with open(clstr_path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            header_match = _CLSTR_HEADER_RE.match(line)
            if header_match:
                current_cluster = int(header_match.group(1))
                continue
            member_match = _CLSTR_MEMBER_RE.match(line)
            if not member_match:
                if line.strip():
                    raise ValueError(f"Unparseable CD-HIT .clstr line: {line!r}")
                continue
            if current_cluster is None:
                raise ValueError(f"Cluster member line before any '>Cluster' header: {line!r}")
            _, length_aa, peptide_id, flag, pct = member_match.groups()
            members.append(
                ClusterMember(
                    cluster_id=current_cluster,
                    peptide_id=peptide_id,
                    length_aa=int(length_aa),
                    is_representative=(flag == "*"),
                    pct_identity_to_representative=None if flag == "*" else float(pct),
                )
            )
    return members


def clusters_to_dataframe(members: list[ClusterMember]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cluster_id": [m.cluster_id for m in members],
            "peptide_id": [m.peptide_id for m in members],
            "length_aa": [m.length_aa for m in members],
            "is_representative": [m.is_representative for m in members],
            "pct_identity_to_representative": [
                m.pct_identity_to_representative for m in members
            ],
        }
    )


def build_cluster_report(
    clusters_df: pd.DataFrame, positive_df: pd.DataFrame, n_input_sequences: int
) -> dict:
    """Before/after summary: counts, tier breakdown, cluster-size distribution."""
    n_output = int(clusters_df["cluster_id"].nunique())
    merged = clusters_df.merge(
        positive_df[["peptide_id", "evidence_tier"]], on="peptide_id", how="left"
    )
    rep_tiers = merged.loc[merged["is_representative"], "evidence_tier"].value_counts()
    cluster_sizes = clusters_df.groupby("cluster_id").size()
    size_distribution = cluster_sizes.value_counts().sort_index()

    n_parsed_members = len(clusters_df)
    if n_parsed_members != n_input_sequences:
        dropped = n_input_sequences - n_parsed_members
    else:
        dropped = 0

    return {
        "n_input_sequences": n_input_sequences,
        "n_parsed_cluster_members": n_parsed_members,
        "n_sequences_dropped_by_cdhit": dropped,  # non-zero => threshold-violation flag
        "n_clusters_after_cdhit90": n_output,
        "representative_tier_counts": {
            str(k): int(v) for k, v in rep_tiers.items()
        },
        "cluster_size_distribution": {
            str(k): int(v) for k, v in size_distribution.items()
        },
        "largest_cluster_size": int(cluster_sizes.max()) if len(cluster_sizes) else 0,
    }
