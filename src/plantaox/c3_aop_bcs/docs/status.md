# Component 3 (AOP-BCS) Status

**Last updated:** 2026-10-18

**Current implementation state:** Task 3.6 complete; Task 3.7 is next and not started

**Legend:** `[x]` completed, `[~]` in progress, `[ ]` incomplete.

The PP1 plan is organized into six phases. Phases 1 and 2 preserve the established structure through completed Task 3.6; Tasks 3.7–3.42 are divided into four proposal-aligned phases. Existing task numbers are preserved for traceability.

# Phase 1 — Research Definition and Project Foundation

## [x] Task 1.1 — Confirm Component 3 responsibility
**Completed:** The proposal defines AOP-BCS as the C3 physicochemical-faithfulness audit and records its C2/C4 interfaces. **Ongoing:** None. **Remaining:** None.

## [x] Task 1.2 — Initial literature study
**Completed:** Initial study covers target predictors, antioxidant residue chemistry, perturbations, SHAP, and reliability evaluation. **Ongoing:** None. **Remaining:** Later literature expansion does not reopen this task.

## [x] Task 1.3 — Define the research problem and gap
**Completed:** Accuracy-only evaluation, missing physicochemical testing, behavioural consistency, and explanation-faithfulness gaps are documented. **Ongoing:** None. **Remaining:** None.

## [x] Task 2.1 — Finalize research objectives
**Completed:** The main objective and dataset, perturbation, audit, metric, SHAP, and comparative objectives are defined. **Ongoing:** None. **Remaining:** None.

## [x] Task 2.2 — Finalize research questions and hypotheses
**Completed:** Research questions, hypothesis pairs, associated tests, and the exploratory BCS-versus-AUROC comparison are defined. **Ongoing:** None. **Remaining:** None.

## [x] Task 2.3 — Freeze the primary experimental protocol
**Completed:** The redox set `{W,Y,H,M,C}`, 3–50 AA range, P1/P2/P3 rules, BLOSUM62 threshold, and delta values are frozen. **Ongoing:** None. **Remaining:** None.

## [x] Task 2.4 — Finalize evaluation metrics
**Completed:** DeltaScore, PFR, IR, FSR, BCS, and SHAP-faithfulness correlation are defined. **Ongoing:** None. **Remaining:** None.

## [x] Task 2.5 — Finalize the methodology and validation plan
**Completed:** The in-silico design, validation, reproducibility, caching, schemas, and statistical plan are documented. **Ongoing:** None. **Remaining:** None.

## [x] Task 2.6 — Complete proposal documentation
**Completed:** The supplied C3 proposal contains the required research, implementation, planning, and supporting sections. **Ongoing:** None. **Remaining:** None for the proposal-stage deliverable.

## [x] Task 3.1 — Prepare the team repository
**Completed:** The team repository and isolated `c3_aop_bcs` source, test, documentation, and data paths are in place. **Ongoing:** None. **Remaining:** None.

## [ ] Task 3.2 — Prepare the Python environment
**Completed:** Confirmed Python 3.13.7, an active project `.venv`, and import availability for pandas, NumPy, SciPy, scikit-learn, pytest, and joblib. The repository interpreter runs the complete C3 test suite. **Ongoing:** None. **Remaining:** Complete repository dependency installation; install/verify Biopython, PyYAML, tqdm, matplotlib, and SHAP when required; then record package versions.

## [x] Task 3.3 — Create the C3 research configuration
**Completed:** Added versioned `research_config.toml`, dependency-free typed loading and strict validation, package exports, and five tests. It records seed `42`, length range `3–50`, redox residues, CD-HIT `0.90`, primary delta `0.05`, sensitivity deltas, and pilot size `20`. **Ongoing:** None. **Remaining:** None.

# Phase 2 — Audit Dataset and Perturbation Pipeline

## [x] Task 3.4 — Acquire the perturbation subject sequences
**Completed:** Preserved four raw CSVs and the versioned `c3_aop_bcs_raw_v1` provenance manifest. Sources contain 917 AnOxPePred assay records and 1,404, 2,120, and 3,022 Multi-AOP records; tests pin schemas, counts, and hashes. **Ongoing:** None. **Remaining:** None; raw files remain immutable.

## [x] Task 3.5 — Standardize sequence records
**Completed:** Added deterministic standardization, five focused tests, and `c3_aop_bcs_standardized_v1` with 3,946 candidates: 699 direct assay-positive E1 plus 676, 1,060, and 1,511 positive Multi-AOP records. Source mapping is preserved; SHA-256 is `dae5f4a4525042ae03cd491dbd820e81e2a9cb55dcac0fb471da7b6409fefa05`. **Ongoing:** None. **Remaining:** Cleaning is delegated to Task 3.6.

## [x] Task 3.6 — Validate and clean sequences
**Completed:** Added deterministic cleaning with mutually exclusive missing, invalid-symbol, length, and duplicate rejection reasons. Exact duplicates retain E1 over E2, then the earliest input record. Generated `c3_aop_bcs_cleaned_v1`, its exclusion ledger, and a versioned report: 3,946 original; 0 missing; 0 invalid; 145 out of range; 2,328 exact duplicates; 1,473 retained. Four focused cleaning tests pass, and the complete C3 suite passes 18 tests. **Ongoing:** None. **Remaining:** None.

# Phase 3 — Dataset Finalization, Perturbation Engine, and Validation

## [ ] Task 3.7 — Apply 90% identity deduplication
**Completed:** None. **Ongoing:** None. **Remaining:** Produce FASTA, run CD-HIT at 90%, preserve clusters, and export representatives and counts.

## [ ] Task 3.8 — Apply the redox-residue eligibility filter
**Completed:** None. **Ongoing:** None. **Remaining:** Retain sequences containing `{W,Y,H,M,C}` and report exclusions.

## [ ] Task 3.9 — Annotate residue positions
**Completed:** None. **Ongoing:** None. **Remaining:** Export positions, residue classes, and redox-position counts.

## [ ] Task 3.10 — Define the perturbation output schema
**Completed:** None. **Ongoing:** None. **Remaining:** Freeze the one-position edit schema and metadata fields.

## [ ] Task 3.11 — Implement P1 alanine scanning
**Completed:** None. **Ongoing:** None. **Remaining:** Implement and validate redox-residue alanine scanning.

## [ ] Task 3.12 — Implement BLOSUM62 support for P2
**Completed:** None. **Ongoing:** None. **Remaining:** Implement deterministic eligible-substitution selection at score `>= +1`.

## [ ] Task 3.13 — Implement P2 conservative substitutions
**Completed:** None. **Ongoing:** None. **Remaining:** Generate and validate non-redox conservative edits.

## [ ] Task 3.14 — Implement P3 random-control substitutions
**Completed:** None. **Ongoing:** None. **Remaining:** Generate deterministic seeded random controls.

## [ ] Task 3.15 — Create a combined perturbation pipeline
**Completed:** None. **Ongoing:** None. **Remaining:** Combine P1/P2/P3 generation, validation, and export.

## [x] Task 3.16 — Create sequence-validation tests
**Completed:** Task 3.6 added passing coverage for valid sequences, empty values, invalid symbols, inclusive minimum/maximum lengths, exact duplicate handling, E1 retention, schemas, counts, hashes, and byte reproducibility. All Task 3.16 checklist cases are verified. **Ongoing:** None. **Remaining:** None.

## [ ] Task 3.17 — Create P1/P2/P3 unit tests
**Completed:** None. **Ongoing:** None. **Remaining:** Add the perturbation correctness and reproducibility tests in `tasks.md`.

## [ ] Task 3.18 — Create reproducibility checks
**Completed:** Configuration and standardization artifacts are byte-reproducible. **Ongoing:** None. **Remaining:** Verify identical combined perturbations and record config/version/seed.

# Phase 4 — Predictor Integration and Pilot Scoring

## [ ] Task 3.19 — Define the common predictor interface
**Completed:** None. **Ongoing:** None. **Remaining:** Define scoring, result, and error-handling contracts.

## [ ] Task 3.20 — Track predictor accessibility
**Completed:** None. **Ongoing:** None. **Remaining:** Verify access, formats, output, batching, licenses, and integration state.

## [ ] Task 3.21 — Prioritize the minimum viable predictor set
**Completed:** None. **Ongoing:** None. **Remaining:** Confirm achievable PP1 scope and the C2 handoff.

## [ ] Task 3.22 — Build a non-experimental dummy/smoke-test predictor
**Completed:** None. **Ongoing:** None. **Remaining:** Add a deterministic software-only smoke-test scorer.

## [ ] Task 3.23 — Implement predictor scoring
**Completed:** None. **Ongoing:** None. **Remaining:** Score originals and variants with caching, restart support, and version metadata.

## [ ] Task 3.24 — Prepare score normalization
**Completed:** None. **Ongoing:** None. **Remaining:** Document and validate comparable score representations.

## [ ] Task 3.25 — Create the PP1 pilot subset
**Completed:** None. **Ongoing:** None. **Remaining:** Select and version a representative seeded 10–30 peptide subset.

# Phase 5 — Behavioural Metrics, Quality Control, and Reproducibility

## [ ] Task 3.26 — Calculate DeltaScore
**Completed:** None. **Ongoing:** None. **Remaining:** Calculate signed/absolute changes and hand-check examples.

## [ ] Task 3.27 — Detect prediction flips and calculate PFR
**Completed:** None. **Ongoing:** None. **Remaining:** Record thresholds/classes/flips and calculate PFR.

## [ ] Task 3.28 — Calculate Invariance Rate (IR)
**Completed:** None. **Ongoing:** None. **Remaining:** Calculate P2 invariance at the primary delta.

## [ ] Task 3.29 — Calculate False Sensitivity Rate (FSR)
**Completed:** None. **Ongoing:** None. **Remaining:** Calculate insufficient P1 response at the primary delta.

## [ ] Task 3.30 — Calculate preliminary BCS
**Completed:** None. **Ongoing:** None. **Remaining:** Calculate and verify preliminary pilot BCS.

## [ ] Task 3.31 — Prepare delta-sensitivity support
**Completed:** Delta values exist in the research configuration. **Ongoing:** None. **Remaining:** Make metrics accept and compare every configured delta.

## [ ] Task 3.32 — Review perturbation counts
**Completed:** None. **Ongoing:** None. **Remaining:** Review P1/P2/P3 totals and zero-variant anomalies.

## [ ] Task 3.33 — Manually inspect example variants
**Completed:** None. **Ongoing:** None. **Remaining:** Record representative manual checks for all perturbation types.

## [ ] Task 3.34 — Create preliminary visualizations
**Completed:** None. **Ongoing:** None. **Remaining:** Create PP1 pilot tables and plots without overstating conclusions.

## [ ] Task 3.35 — Create run manifests and provenance records
**Completed:** Dataset provenance exists for Tasks 3.4–3.5. **Ongoing:** None. **Remaining:** Add experiment-level config, code, model, seed, input, and output provenance.

## [ ] Task 3.36 — Prepare the SHAP-faithfulness data structure
**Completed:** The planned correlation is documented. **Ongoing:** None. **Remaining:** Define the SHAP/DeltaScore structure; full analysis remains post-PP1.

# Phase 6 — PP1 Documentation, Evidence, and Delivery

## [ ] Task 3.37 — Update implementation documentation
**Completed:** Task and status tracking reflect current implementation through Task 3.6. **Ongoing:** None. **Remaining:** Add final usage, schemas, assumptions, limitations, and architecture.

## [ ] Task 3.38 — Maintain Git history
**Completed:** Tasks 3.3–3.6, reproducibility corrections, and the earlier phase-tracking update have focused descriptive commits. **Ongoing:** Commit every logical checkpoint. **Remaining:** Push/update through the team workflow and verify final history.

## [ ] Task 3.39 — Update the research logbook
**Completed:** Milestones are preserved in status records and Git history. **Ongoing:** None. **Remaining:** Transfer required evidence to the formal logbook.

## [ ] Task 3.40 — Prepare PP1 evidence
**Completed:** Configuration, source, provenance, standardized data, and tests provide initial evidence. **Ongoing:** None. **Remaining:** Capture pipeline, tests, samples, metrics, and provenance evidence.

## [ ] Task 3.41 — Prepare the PP1 presentation
**Completed:** None. **Ongoing:** None. **Remaining:** Build the C3 PP1 presentation from verified pilot results.

## [ ] Task 3.42 — PP1 rehearsal and final verification
**Completed:** None. **Ongoing:** None. **Remaining:** Run the pilot cleanly, reconcile evidence, state limitations, and rehearse.

# Scope guard

- All implementation changes remain restricted to paths containing `c3_aop_bcs`.
- Raw source datasets are preserved unchanged.
- `tasks.md` and this status record must be updated together whenever task state changes.
