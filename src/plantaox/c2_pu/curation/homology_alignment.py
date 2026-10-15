"""Bucket 2.6 -- EMBOSS needleall-based pairwise alignment for the external
inactive-control homology audit (and reusable anywhere a real alignment,
not a CD-HIT percent-identity shortcut, is needed for short peptides).

CD-HIT's percent-identity is normalized by the shorter sequence's length,
which this project has already found to be unreliable for very short
peptides (see Bucket 2.4's audit, where it produced large, biologically
meaningless mixed clusters). EMBOSS ``needleall`` instead runs a real
global (Needleman-Wunsch) alignment for every pair in one batched call and
reports identity, similarity, gaps, and alignment length directly --
``-aformat pair`` gives the full per-pair block (same format as a single
``needle`` run), parsed here the same way Bucket 2.4's Decision B alignment
was read and reported manually.
"""

from __future__ import annotations

import re
from pathlib import Path

from plantaox.c2_pu.common.wsl import run_in_conda_env, to_wsl_path

_BLOCK_RE = re.compile(
    r"# 1: (?P<seq1>\S+)\n"
    r"# 2: (?P<seq2>\S+)\n"
    r".*?"
    r"# Length: (?P<length>\d+)\n"
    r"# Identity:\s+(?P<identity_n>\d+)/(?P<identity_d>\d+)\s*\(\s*(?P<identity_pct>[\d.]+)%\)\n"
    r"# Similarity:\s+(?P<similarity_n>\d+)/(?P<similarity_d>\d+)\s*\(\s*(?P<similarity_pct>[\d.]+)%\)\n"
    r"# Gaps:\s+(?P<gaps_n>\d+)/(?P<gaps_d>\d+)\s*\(\s*(?P<gaps_pct>[\d.]+)%\)\n"
    r"# Score: (?P<score>[\d.-]+)",
    re.DOTALL,
)


def run_needleall(
    asequence_fasta: Path,
    bsequence_fasta: Path,
    output_path: Path,
    gapopen: float = 10.0,
    gapextend: float = 0.5,
    minscore: float = -10_000.0,
    timeout: int = 1800,
) -> Path:
    """Batched many-to-many global alignment (inside WSL pu_aop). Every
    sequence in ``asequence_fasta`` is aligned against every sequence in
    ``bsequence_fasta`` -- N*M pairs in one call.

    ``minscore`` is deliberately set far below needleall's own default
    (1.0), which silently DROPS any pair scoring below it from the output
    -- confirmed empirically (an N=38, M=1205 run returned only 35,076 of
    the expected 45,790 pairs at the default). For a completeness-audited
    homology scan every pair must be accounted for, including the
    irrelevant negative-score ones, so this is set low enough that nothing
    is ever silently excluded.
    """
    result = run_in_conda_env(
        [
            "needleall",
            "-asequence", to_wsl_path(asequence_fasta),
            "-bsequence", to_wsl_path(bsequence_fasta),
            "-sprotein1", "-sprotein2",
            "-gapopen", str(gapopen),
            "-gapextend", str(gapextend),
            "-minscore", str(minscore),
            "-outfile", to_wsl_path(output_path),
            "-aformat", "pair",
            "-auto",
        ],
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"needleall failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}")
    if not output_path.exists():
        raise RuntimeError(f"needleall reported success but {output_path} was not written:\n{result.stdout}")
    return output_path


def parse_needleall_pairs(output_path: Path) -> list[dict]:
    """Parse every aligned pair's identity/similarity/gaps/length/score
    from a ``-aformat pair`` needleall output file."""
    text = output_path.read_text(encoding="utf-8", errors="replace")
    pairs = []
    for match in _BLOCK_RE.finditer(text):
        pairs.append(
            {
                "seq1_id": match.group("seq1"),
                "seq2_id": match.group("seq2"),
                "alignment_length": int(match.group("length")),
                "identity_count": int(match.group("identity_n")),
                "identity_denominator": int(match.group("identity_d")),
                "identity_pct": float(match.group("identity_pct")),
                "similarity_count": int(match.group("similarity_n")),
                "similarity_pct": float(match.group("similarity_pct")),
                "gaps_count": int(match.group("gaps_n")),
                "gaps_pct": float(match.group("gaps_pct")),
                "score": float(match.group("score")),
            }
        )
    return pairs
