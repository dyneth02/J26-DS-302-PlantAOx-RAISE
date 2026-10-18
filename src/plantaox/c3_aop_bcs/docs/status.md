# Component 3 (AOP-BCS) Status

**Last updated:** 2026-10-18

## Completed work

- Completed the Component 3 research definition, initial literature study, research-gap analysis, objectives, research questions, hypotheses, experimental protocol, evaluation metrics, methodology, validation plan, and proposal documentation.
- Prepared the isolated `c3_aop_bcs` repository structure for source code, tests, documentation, and data artifacts.
- Created the versioned C3 research configuration containing random seed `42`, sequence length range `3–50`, redox residues `{W,Y,H,M,C}`, CD-HIT threshold `0.90`, primary delta `0.05`, sensitivity deltas `0.02`, `0.05`, and `0.10`, and pilot size `20`.
- Added a dependency-free typed configuration loader with strict validation and focused tests.
- Verified Python 3.13.7 and the project `.venv`; pandas, NumPy, SciPy, scikit-learn, pytest, joblib, and Biopython currently import successfully.
- Installed Biopython `1.88` in the project `.venv` and verified `Bio.Align.substitution_matrices.load("BLOSUM62")`, including the expected D-to-E score of `2.0`.
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
- Applied reproducible 90% identity deduplication to the complete cleaned dataset using the real CD-HIT 4.8.1 executable at `/usr/bin/cd-hit` in the `Ubuntu-24.04` WSL distribution.
- Converted all 1,473 cleaned sequences to deterministic FASTA, retained 1,046 representative sequences across 1,046 clusters, and removed 427 sequences at the configured 0.90 identity threshold.
- Preserved the native CD-HIT representative FASTA and `.clstr` output, and generated traceable representative and cluster-membership CSV tables.
- Added a versioned `c3_aop_bcs_cd_hit_90_v1` report containing the source checksum, exact CD-HIT command and parameters, tool/runtime version, counts, and SHA-256 checksums for every generated artifact.
- Applied the configured `{W,Y,H,M,C}` redox-residue eligibility rule to all 1,046 CD-HIT representatives, retaining 734 primary P1 audit subjects and rejecting 312 sequences with no redox residue.
- Generated the versioned `c3_aop_bcs_redox_eligible_v1` subject table, a complete exclusion ledger using the reason `no_redox_residue`, and a report containing the rule, input checksum, reconciled counts, and output checksums.
- Preserved every Task 3.7 source, evidence, raw-record, and CD-HIT provenance field in both eligible and excluded records, while adding redox occurrence counts and the configured residues present.
- Expanded all 734 eligible peptides into 5,580 deterministic one-based residue annotations: 1,180 redox positions and 4,400 non-redox positions.
- Recorded each position's residue and `redox`/`non_redox` classification, repeated the validated peptide-level redox-position count, and preserved every Task 3.8 provenance field.
- Generated the versioned `c3_aop_bcs_residue_annotations_v1` table and a reproducibility report containing the annotation rule, configured redox set, source checksum, reconciled counts, and output checksum.
- Froze perturbation schema version `1.0` with ordered fields for schema and variant identifiers, sequence linkage, original and perturbed sequences, one-based position, original and substituted residues, perturbation type, BLOSUM62 score, random seed, and random metadata.
- Added an immutable perturbation-record model with strict construction and CSV mapping, standard-amino-acid validation, same-length enforcement, and proof that each record contains exactly one edit at its declared position.
- Defined explicit metadata applicability: P1 carries no P2/P3 metadata, P2 requires a BLOSUM62 score, and P3 requires a random seed plus canonical JSON metadata.
- Added a deterministic machine-readable `perturbation_schema_v1.json` contract shared by the future P1, P2, and P3 generators.
- Implemented deterministic P1 alanine scanning over every configured W/Y/H/M/C position in the residue annotation dataset.
- Generated 1,180 independently validated P1 variants across all 734 eligible peptides: 189 W, 398 Y, 303 H, 176 M, and 114 C substitutions to alanine.
- Exported `c3_aop_bcs_p1_alanine_v1` using the frozen perturbation schema, with stable variant identifiers and a report pinning the source annotation and schema checksums, rule, counts, and output checksum.
- Verified every P1 variant changes exactly one declared redox position to alanine, preserves sequence length, contains no P2/P3 metadata, and covers every annotated redox position exactly once.
- Reimplemented Task 3.12 using Biopython `1.88`: BLOSUM62 is loaded through `Bio.Align.substitution_matrices.load("BLOSUM62")`, then restricted to the project's 20 standard amino acids and validated for integral, symmetric scores.
- Implemented P2 candidate evaluation that excludes the original residue, alanine, and W/Y/H/M/C, then keeps only substitutions scoring at least `+1`.
- Implemented deterministic selection by highest BLOSUM62 score followed by alphabetical residue code, returning no selection when the frozen rule has no eligible candidate.
- Updated the versioned `c3_aop_bcs_blosum62_support_v1` manifest to record the Biopython version, loader API, matrix identifier, library alphabet, standard-amino-acid dimensions, selection rules, and selected substitution for every non-redox original residue.
- Removed the obsolete bundled BLOSUM62 TSV so the implementation has one unambiguous matrix source through Biopython.
- Implemented deterministic P2 generation over the 4,400 annotated non-redox positions, applying the frozen Biopython BLOSUM62 selection rule independently at each position.
- Generated 3,276 validated P2 variants across 695 peptides; the remaining 1,124 non-redox positions were explicitly skipped because F, G, or P had no eligible substitution under the frozen exclusions and `>= +1` threshold.
- Exported `c3_aop_bcs_p2_conservative_v1` using the frozen perturbation schema, including one-based mutation positions, original and substituted residues, perturbed sequences, and selected BLOSUM62 scores.
- Added a checksum-backed P2 report pinning the residue-annotation source, perturbation schema, Biopython BLOSUM62 support manifest, selection rules, reconciled counts, per-residue summaries, and output checksum.
- Verified every P2 record changes exactly one non-redox position, preserves sequence length, excludes alanine and W/Y/H/M/C as replacements, and has a BLOSUM62 score of at least `+1`.
- Confirmed all 49 current C3 tests pass with 43 subtests, including committed-dataset coverage, deterministic byte output, skipped-position accounting, Biopython matrix loading, candidate exclusions, minimum-score filtering, deterministic selection, and perturbation-schema validation.
- Reorganized the PP1 checklist into six proposal-aligned phases and converted every subtask into an individually tracked Markdown checkbox.
- Maintained focused Git commits for Tasks 3.3–3.13 and the associated documentation and reproducibility updates.

## Current task — Task 3.14: Implement P3 random-control substitutions

**Status:** In progress.

Current work:

- generate valid one-position random-control substitutions;
- derive reproducible per-sequence and per-position choices from the configured master seed;
- store the random seed and canonical random-control metadata;
- export and validate deterministic P3 variants with complete count and provenance reporting.
