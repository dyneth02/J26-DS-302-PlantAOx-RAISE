# C4 FR1 Candidate Generation Acceptance

**Status:** PASS (repository artifacts/tests); supervisor review pending.

- Reviewed FASTA sources, taxonomy filters, exclusions, and checksums: `SCREEN_PP1_DATA_AND_OUTPUTS.md` and raw registry.
- Candidate funnel and plant counts: `PP1_NUMBERS.md`, `data/interim/c4_screen/funnel_summary.csv`.
- Combined candidates: 152,259 unique sequences; `candidates.parquet`, `candidates.fasta`, `plant_membership.parquet`. FASTA SHA-256: `bcf23050ebdcba94940043ad4b959d3659f9a7bc2c6734de401453479e96b3c7`.
- Implementation: `digest.py`, `filters.py`, `dedup.py`, `descriptors.py`; C4 tests pass as part of 14/14 suite.
- Known deviation: BIOPEP spot-check deferred; pyteomics pepsin pH 1.3 is nearest installed rule to proposal pH 1.2.
- Handoff is prepared in `C4_CANDIDATE_FASTA_HANDOFF.md`; external delivery cannot be re-verified here.
