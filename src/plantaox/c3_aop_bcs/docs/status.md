# Component 3 (AOP-BCS) Status

**Last updated:** 2026-10-19

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
- Implemented P3 random-control generation for every annotated residue position using the configured master seed `42` and a versioned SHA-256 modulo selection rule over the 19 alphabetically ordered alternatives that exclude the original residue.
- Derived every P3 choice independently from the master seed, sequence ID, original sequence, one-based position, and original residue, making choices reproducible and independent of input row order.
- Generated 5,580 independently validated P3 variants across all 734 eligible peptides and stored the master seed plus canonical JSON metadata containing the selection algorithm, candidate index/count, and position-specific SHA-256 seed digest.
- Exported `c3_aop_bcs_p3_random_control_v1` using the frozen perturbation schema and added a checksum-backed report pinning the source annotation, schema, master seed, seed derivation, counts, and output checksum.
- Verified every P3 variant changes exactly one declared position, uses a valid standard amino acid different from the original, preserves sequence length, and reproduces byte-identical output for the same input and seed.
- Implemented a unified Task 3.15 pipeline that accepts the annotated peptide dataset and runs the P1, P2, and P3 generators in a single deterministic workflow.
- Added source-linked automatic validation that rechecks frozen-schema invariants and perturbation-specific P1, P2, and P3 semantics, including duplicate variant identifiers.
- Added deterministic rejection handling: invalid generated variants are excluded from the accepted output and written with explicit reasons to a separate rejection ledger.
- Generated `c3_aop_bcs_combined_perturbations_v1` with 10,036 accepted variants—1,180 P1, 3,276 P2, and 5,580 P3—and zero rejected variants from the verified production inputs.
- Added a checksum-backed combined pipeline report recording the source annotations, complete research configuration, schema and generator versions, per-type generated/accepted/rejected counts, validation policy, and both output checksums.
- Verified the combined CSV exactly matches the ordered union of the independently verified P1, P2, and P3 datasets and added tests proving deliberately invalid semantic records and duplicate IDs are rejected.
- Implemented a Task 3.18 reproducibility runner that executes the complete production perturbation workflow twice from the same 5,580-position annotation input and the same research configuration.
- Confirmed both production runs generated the same 10,036 accepted variants and zero rejections, with byte-identical accepted outputs and rejection ledgers.
- Confirmed the 5,580 P3 random-control records are byte-identical across both runs under master seed `42`.
- Added the versioned `c3_aop_bcs_perturbation_reproducibility_v1` evidence report with a `PASS` result, per-run counts, byte sizes, SHA-256 hashes, full configuration snapshots, seed, Python/Biopython versions, pipeline/schema/generator versions, and BLOSUM62-support checksum.
- Added tests verifying deterministic evidence generation on repeated complete runs and confirming the production evidence matches the committed combined and P3 outputs.
- Defined the versioned Task 3.19 common predictor contract with the operation `score(sequence: str) -> float`, stable predictor identity/display-name/version metadata, and a runtime-checkable protocol for downstream C3 code.
- Added an architecture-neutral base adapter that validates uppercase standard-amino-acid inputs, invokes predictor-specific scoring behind a protected boundary, and always returns a finite built-in `float`.
- Added a generic callable adapter capable of wrapping functions, object methods, local models, scripts, or service clients without exposing their internal architecture to the C3 scoring pipeline.
- Defined distinct errors for invalid sequence input, unavailable predictor resources, predictor execution failures, and non-numeric or non-finite returned scores.
- Added a deterministic machine-readable `predictor_interface_v1.json` contract documenting the input/output boundary, required metadata, architecture isolation rule, and error semantics.
- Confirmed all 69 current C3 tests pass with 54 subtests, including interface conformance across different adapter shapes, invalid input/score rejection, failure normalization, deterministic contract generation, and all prior C3 behavior.
- Completed a source-backed accessibility review of AnOxPePred, Multi-AOP, AOPxSVM, AOP-DRL, and Component 2's PU-AOP using current public repositories, primary publications/services, and the local repository state.
- Added the versioned `predictor_access_status_v1.json` registry with inspected repository revisions, code/model/service availability, expected inputs, output semantics, batch support, licence/access limits, evidence locations, blockers, and C3 integration state.
- Added a generated human-readable predictor access table and a validator that refuses an `integrated` status unless a real finite score and retained score evidence are both recorded.
- Confirmed AnOxPePred, Multi-AOP, and AOPxSVM provide public model artifacts; AOP-DRL lacks a public trained checkpoint/inference package and its published endpoint currently redirects to an unrelated login page.
- Confirmed PU-AOP source and manifests are present, but its required ignored checkpoint/cache artifacts and documented external backup are absent from this checkout.
- Kept all five predictors explicitly `not_integrated` because none has yet produced a retained real score through the C3 predictor interface.
- Confirmed all 73 current C3 tests pass with 64 subtests, including registry completeness, operational limitations, integration-claim enforcement, and deterministic Markdown rendering.
- Reorganized the PP1 checklist into six proposal-aligned phases and converted every subtask into an individually tracked Markdown checkbox.
- Maintained focused Git commits for Tasks 3.3–3.20 and the associated documentation and reproducibility updates.

## Current task — Task 3.21: Prioritize the minimum viable predictor set

**Status:** In progress.

Current work:

- prioritize AnOxPePred, AOPxSVM, and PU-AOP for the minimum viable PP1 predictor set using the Task 3.20 evidence;
- coordinate the frozen PU-AOP model/scaler/cache handoff with Component 2;
- treat Multi-AOP and AOP-DRL as secondary where their environment, licensing, or missing-artifact constraints prevent timely verified scoring;
- document every unresolved access issue and keep integration claims tied to retained real-score evidence.
