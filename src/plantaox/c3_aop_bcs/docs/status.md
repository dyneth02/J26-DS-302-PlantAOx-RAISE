# Component 3 (AOP-BCS) Status

**Last updated:** 2026-10-18

## Completed work

- Completed the Component 3 research definition, initial literature study, research-gap analysis, objectives, research questions, hypotheses, experimental protocol, evaluation metrics, methodology, validation plan, and proposal documentation.
- Prepared the isolated `c3_aop_bcs` repository structure for source code, tests, documentation, and data artifacts.
- Created the versioned C3 research configuration containing random seed `42`, sequence length range `3–50`, redox residues `{W,Y,H,M,C}`, CD-HIT threshold `0.90`, primary delta `0.05`, sensitivity deltas `0.02`, `0.05`, and `0.10`, and pilot size `20`.
- Added a dependency-free typed configuration loader with strict validation and focused tests.
- Verified Python 3.13.7 and the project `.venv`; pandas, NumPy, SciPy, scikit-learn, pytest, and joblib currently import successfully.
- Acquired and preserved four original C3 source datasets under `data/raw/c3_aop_bcs/` without manually editing them.
- Added the versioned `c3_aop_bcs_raw_v1` provenance manifest with source locations, schemas, row counts, acquisition information, evidence notes, byte counts, and SHA-256 hashes.
- Verified the acquired source data: 917 AnOxPePred assay records and 1,404, 2,120, and 3,022 records from the three Multi-AOP benchmarks.
- Implemented deterministic sequence standardization with uppercase conversion, whitespace removal, stable sequence identifiers, and preserved raw-source mappings.
- Generated `c3_aop_bcs_standardized_v1` containing 3,946 candidate-positive records: 699 direct assay-positive E1 candidates and 676, 1,060, and 1,511 positive Multi-AOP candidates.
- Added a versioned standardization report and reproducibility checks; the standardized CSV SHA-256 is `dae5f4a4525042ae03cd491dbd820e81e2a9cb55dcac0fb471da7b6409fefa05`.
- Implemented deterministic sequence cleaning with mutually exclusive rejection reasons for missing sequences, invalid symbols, out-of-range lengths, and exact duplicates.
- Applied the standard 20-amino-acid alphabet and inclusive 3–50 AA length rules.
- Applied deterministic exact deduplication that retains E1 evidence over E2 evidence and otherwise keeps the earliest standardized record.
- Generated `c3_aop_bcs_cleaned_v1` and its exclusion ledger: 3,946 original records, 0 missing, 0 invalid, 145 out of range, 2,328 exact duplicates, and 1,473 retained sequences.
- Completed the sequence-validation checks originally listed under Task 3.16 through the Task 3.6 implementation: valid sequences, invalid symbols, empty values, minimum/maximum lengths, and duplicate handling.
- Confirmed all 18 current C3 tests pass, including deterministic artifact, schema, count, checksum, and byte-reproducibility checks.
- Reorganized the PP1 checklist into six proposal-aligned phases and converted every subtask into an individually tracked Markdown checkbox.
- Maintained focused Git commits for Tasks 3.3–3.6 and the associated documentation and reproducibility updates.

## Next task — Task 3.7: Apply 90% identity deduplication

**Status:** Not started. No implementation task is currently in progress.

The next work will:

- convert the cleaned sequences to FASTA;
- run CD-HIT at the configured `0.90` identity threshold;
- preserve the CD-HIT cluster output;
- convert representative sequences back to the working table format;
- record the input count, representative count, and cluster count;
- verify the generated artifacts and update both `tasks.md` and this file immediately as each subtask is completed.
