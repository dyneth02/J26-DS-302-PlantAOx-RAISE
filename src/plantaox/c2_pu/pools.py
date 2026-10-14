"""FR2 (Bucket 2.1) — C1 random-decoy pool: secondary blocklist, deterministic
sampling, and leakage-audit cleanup against the frozen FR1 positive pool.

Ports the UniProtKB query + secondary keyword blocklist + seed-42 sampling
procedure documented in PU_AOP_RESEARCH_CONTEXT.md §5 into tested, reproducible
code. Verified against the existing artifacts before any cleanup logic was
written: re-applying ``BIOACTIVITY_KEYWORDS`` to the saved 8,830-candidate
pool reproduces exactly 8,233 kept / 597 excluded (the documented provenance
numbers), and ``random.seed(42); random.sample(kept, 5000)`` over that kept
list reproduces ``stage_c1_decoys.fasta`` byte-for-byte (verified by header+
sequence set equality, not just counts).

C2/C3 pool construction (Bucket 2.2/2.3) will be added to this module later;
this file currently only implements C1.
"""

from __future__ import annotations

import random
import re

from plantaox.c2_pu.common.sequence import STANDARD_AMINO_ACIDS, is_standard_alphabet

# Canonical list, as documented in PU_AOP_RESEARCH_CONTEXT.md section 5.
# AGENTS.md rule: extend this list, never regenerate it from scratch, and
# never remove an entry without a logged reason in IMPLEMENTATION_STATUS.md.
BIOACTIVITY_KEYWORDS = [
    kw.lower()
    for kw in [
        "antioxidant",
        "antimicrobial",
        "antihypertensive",
        "antifungal",
        "anticancer",
        "anti-inflammatory",
        "bioactive",
        "antibacterial",
        "antiviral",
        "chelat",
        "toxin",
        "venom",
        "neurotoxin",
        "hormone",
        "neuropeptide",
        "inhibitor",
        "lectin",
        "defensin",
        "cecropin",
        "magainin",
        "temporin",
        "contryphan",
        "conotoxin",
        "kinin",
        "tachykinin",
        "allatotropin",
        "allatostatin",
        "tropin",
        "cyclotide",
        "cupiennin",
        "signiferin",
        "tryptophyllin",
        "formaecin",
        "corazonin",
        "ampulexin",
        "myosuppressin",
        "fmrfamide",
        "antimicrobial peptide",
        "amp",
        "superoxide dismutase",
        "peroxidase",
        "catalase",
        "glutathione",
        "thioredoxin",
        "ferredoxin reductase",
        "metallothionein",
    ]
]

C1_SAMPLE_SIZE = 5000
C1_SEED = 42

_UNIPROT_HEADER_RE = re.compile(
    r"^(?P<db>\w+)\|(?P<accession>[^|]+)\|(?P<entry_name>\S+)\s+(?P<rest>.*)$"
)


def matches_bioactivity_blocklist(header: str) -> bool:
    """True if any blocklist keyword appears in the (lowercased) FASTA header."""
    desc = header.lower()
    return any(kw in desc for kw in BIOACTIVITY_KEYWORDS)


def apply_secondary_blocklist(
    candidates: list[tuple[str, str]]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split (header, sequence) candidates into (kept, excluded) by the blocklist."""
    kept, excluded = [], []
    for header, seq in candidates:
        (excluded if matches_bioactivity_blocklist(header) else kept).append((header, seq))
    return kept, excluded


def sample_c1_decoys(
    kept_candidates: list[tuple[str, str]], n: int = C1_SAMPLE_SIZE, seed: int = C1_SEED
) -> list[tuple[str, str]]:
    """Reproduce the original deterministic C1 sample (seed 42, random.sample
    over the candidate list in its on-disk order)."""
    random.seed(seed)
    return random.sample(kept_candidates, n)


def find_contamination(
    c1_records: list[tuple[str, str]], screen_sequences: set[str]
) -> list[tuple[str, str]]:
    """Return every C1 record whose sequence exactly matches a screened
    (positive-pool or conflict) sequence."""
    return [(h, s) for h, s in c1_records if s in screen_sequences]


def select_replacements(
    eligible_candidates: list[tuple[str, str]], n_needed: int, seed: int = C1_SEED
) -> list[tuple[str, str]]:
    """Deterministically select ``n_needed`` replacements from the leftover
    eligible candidate pool (same seed convention as the original sample, but
    scoped to this draw so it doesn't depend on how many sequences preceded
    it in the original sampling call)."""
    random.seed(seed)
    return random.sample(eligible_candidates, n_needed)


def parse_uniprot_header(header: str) -> dict:
    """Parse a UniProtKB FASTA defline into its component fields.

    Example: "sp|Q10582|ANGT2_BOTJA Angiotensin-like peptide 2 (Fragment)
    OS=Bothrops jararaca OX=8724 PE=1 SV=1"
    """
    match = _UNIPROT_HEADER_RE.match(header)
    if not match:
        return {
            "db": None,
            "accession": None,
            "entry_name": None,
            "description": header,
            "organism": None,
            "is_fragment": False,
        }
    rest = match.group("rest")
    os_match = re.search(r"OS=(.*?)(?:\s+OX=|\s+GN=|\s+PE=|\s+SV=|$)", rest)
    description = re.split(r"\s+OS=", rest)[0]
    return {
        "db": match.group("db"),
        "accession": match.group("accession"),
        "entry_name": match.group("entry_name"),
        "description": description,
        "organism": os_match.group(1) if os_match else None,
        "is_fragment": "(Fragment)" in rest,
    }


def clean_c1_pool(
    c1_records: list[tuple[str, str]],
    candidate_pool_records: list[tuple[str, str]],
    screen_sequences: set[str],
    seed: int = C1_SEED,
) -> tuple[list[tuple[str, str]], list[dict], list[dict], dict]:
    """Resolve leakage in the existing C1 pool without resampling it wholesale.

    ``candidate_pool_records`` is the full query-level candidate universe
    (``uniprotkb_candidates.fasta``, pre-secondary-blocklist) -- this
    function re-applies the blocklist itself to derive the eligible
    replacement pool, so it never needs a live UniProt query.

    Returns (clean_records, exclusion_log, replacement_log, summary).
    ``clean_records`` has the same length as ``c1_records`` (contaminated
    entries swapped 1:1 for replacements) unless the eligible pool runs out
    of candidates, in which case fewer replacements are made and the summary
    reports the shortfall explicitly rather than silently under-filling.
    """
    contaminated = find_contamination(c1_records, screen_sequences)
    contaminated_seqs = {s for _, s in contaminated}
    clean_records = [(h, s) for h, s in c1_records if s not in contaminated_seqs]

    kept_candidates, _ = apply_secondary_blocklist(candidate_pool_records)
    current_seqs = {s for _, s in c1_records}
    eligible_replacements = [
        (h, s)
        for h, s in kept_candidates
        if s not in current_seqs and s not in screen_sequences
    ]

    n_needed = len(c1_records) - len(clean_records)
    n_available = len(eligible_replacements)
    n_selected = min(n_needed, n_available)
    replacements = (
        select_replacements(eligible_replacements, n_selected, seed=seed)
        if n_selected > 0
        else []
    )
    clean_records = clean_records + replacements

    exclusion_log = [
        {
            "header": h,
            "sequence": s,
            "length": len(s),
            "reason": "exact_sequence_match_against_fr1_positive_or_conflict",
            **parse_uniprot_header(h),
        }
        for h, s in contaminated
    ]
    replacement_log = [
        {
            "header": h,
            "sequence": s,
            "length": len(s),
            "source": "uniprotkb_candidates.fasta (post-secondary-blocklist, not in original sample)",
            **parse_uniprot_header(h),
        }
        for h, s in replacements
    ]

    summary = {
        "n_input_records": len(c1_records),
        "n_contaminated_removed": len(contaminated),
        "n_replacements_needed": n_needed,
        "n_replacements_available": n_available,
        "n_replacements_made": n_selected,
        "n_output_records": len(clean_records),
        "shortfall": n_needed - n_selected,
        "n_unique_sequences_output": len(set(s for _, s in clean_records)),
    }
    return clean_records, exclusion_log, replacement_log, summary


def find_non_standard_alphabet(records: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Return every record whose sequence contains a residue outside the
    standard 20-amino-acid alphabet (X/B/Z/U/etc.) -- never silently
    translated or dropped elsewhere; this is the detection step only."""
    return [(h, s) for h, s in records if not is_standard_alphabet(s)]


def clean_c1_alphabet(
    c1_records: list[tuple[str, str]],
    candidate_pool_records: list[tuple[str, str]],
    screen_sequences: set[str],
    seed: int = C1_SEED,
) -> tuple[list[tuple[str, str]], list[dict], list[dict], dict]:
    """Enforce the standard-20-amino-acid-alphabet policy on an already
    leakage-clean C1 pool (2026-10-14 project-owner decision: sequences with
    X/B/Z/U are ineligible for the ESM-2/physicochemical modeling pipeline).

    Mirrors ``clean_c1_pool``'s swap-not-resample pattern: non-standard
    records are removed and deterministically replaced 1:1 from the same
    candidate universe (``uniprotkb_candidates.fasta``), re-screened against
    the secondary bioactivity blocklist, all screened positive/conflict
    sequences, AND the new alphabet requirement itself -- so a replacement
    can never itself be non-standard, blocklisted, or a leaked positive.

    Returns (clean_records, exclusion_log, replacement_log, summary), same
    shape as ``clean_c1_pool``.
    """
    non_standard = find_non_standard_alphabet(c1_records)
    non_standard_seqs = {s for _, s in non_standard}
    clean_records = [(h, s) for h, s in c1_records if s not in non_standard_seqs]

    kept_candidates, _ = apply_secondary_blocklist(candidate_pool_records)
    current_seqs = {s for _, s in c1_records}
    eligible_replacements = [
        (h, s)
        for h, s in kept_candidates
        if s not in current_seqs
        and s not in screen_sequences
        and is_standard_alphabet(s)
    ]

    n_needed = len(c1_records) - len(clean_records)
    n_available = len(eligible_replacements)
    n_selected = min(n_needed, n_available)
    replacements = (
        select_replacements(eligible_replacements, n_selected, seed=seed)
        if n_selected > 0
        else []
    )
    clean_records = clean_records + replacements

    exclusion_log = [
        {
            "header": h,
            "sequence": s,
            "length": len(s),
            "reason": "non_standard_alphabet_residue",
            "non_standard_residues": sorted(set(s) - set(STANDARD_AMINO_ACIDS)),
            **parse_uniprot_header(h),
        }
        for h, s in non_standard
    ]
    replacement_log = [
        {
            "header": h,
            "sequence": s,
            "length": len(s),
            "source": "uniprotkb_candidates.fasta (post-secondary-blocklist, standard-alphabet, "
            "not in original sample, not a screened positive/conflict)",
            **parse_uniprot_header(h),
        }
        for h, s in replacements
    ]

    summary = {
        "n_input_records": len(c1_records),
        "n_non_standard_removed": len(non_standard),
        "n_replacements_needed": n_needed,
        "n_replacements_available": n_available,
        "n_replacements_made": n_selected,
        "n_output_records": len(clean_records),
        "shortfall": n_needed - n_selected,
        "n_unique_sequences_output": len(set(s for _, s in clean_records)),
    }
    return clean_records, exclusion_log, replacement_log, summary
