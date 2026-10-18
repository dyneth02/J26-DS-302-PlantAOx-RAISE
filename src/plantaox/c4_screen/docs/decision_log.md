# Decision log

## Component 4 — candidate generation

- **Proteome scope:** use UniProt Swiss-Prot reviewed entries selected by taxonomy ID. The proposal's proteome identifiers include unreviewed entries, so reviewed-only counts and exclusions are recorded separately.
- **Digestion implementation:** use the installed `pyteomics` Expasy-style rules rather than a BIOPEP-UWM batch workflow. Installed `pyteomics 5.0.1` provides the exact rule names `pepsin ph1.3` and `trypsin`; pepsin pH 1.3 is the nearest available rule to proposed pH 1.2.
- **Deduplication:** exact sequence equality within and across plants; preserve every parent accession and 1-based inclusive position. CD-HIT is deferred. At 90% identity, peptides up to 9 residues cannot have a non-identical sequence meeting the threshold; optional clustering for lengths 10–20 remains a later decision.
- **Signals:** signal inputs remain mock-only and must retain `source="mock"`. The config's BCS flag thresholds are explicitly `C4-provisional`; this Gate 1 does not generate or evaluate signals.
