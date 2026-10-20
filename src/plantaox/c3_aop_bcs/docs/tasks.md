# Component 3 (AOP-BCS) — Work Plan Up to Progress Presentation 1 (PP1)

**Component:** Component 3 — AOP-BCS  
**Title:** *Physicochemical Faithfulness Audit for Antioxidant Peptide Predictors via Controlled Sequence Perturbation Benchmarking*  
**Project:** PlantAOx-RAISE  
**Scope of this plan:** Work to be completed from the beginning of the project up to **Progress Presentation 1 (PP1)**.

> This task plan is derived from the Component 3 proposal report, especially the objectives, methodology, validation strategy, functional/non-functional requirements, development phases, WBS/Gantt structure, and the C3 task definition.  
> The PP1 implementation target is a **working and validated pilot audit pipeline**, not the complete final multi-predictor statistical/SHAP study.

> Every subtask is tracked independently. In Markdown Preview, `- [x]` displays a checked box (✓) for verified work and `- [ ]` displays an unchecked box for incomplete work.

---

# Phase 1 — Research Definition and Project Foundation

## Task 1.1 — Confirm Component 3 responsibility

### Subtasks
- [x] Confirm Component 3 research title: **AOP-BCS**.
- [x] Confirm the individual responsibility boundary of Component 3.
- [x] Confirm how C3 connects to:
  - [x] Component 2: receives the PU-AOP predictor for auditing.
  - [x] Component 4: provides predictor-level reliability evidence.
- [x] Confirm that C3 is an **audit framework**, not a new AOP classifier.
- [x] Record the component scope in the project documentation and logbook.

### Deliverable
- Confirmed C3 scope and responsibility statement.

---

## Task 1.2 — Initial literature study

### Subtasks
- [x] Study existing AOP predictors:
  - [x] AnOxPePred
  - [x] Multi-AOP
  - [x] AOPxSVM
  - [x] AOP-DRL
  - [x] PU-AOP from Component 2
- [x] Study antioxidant-relevant amino-acid chemistry.
- [x] Study evidence supporting the fixed redox residue set:
  - [x] W — Tryptophan
  - [x] Y — Tyrosine
  - [x] H — Histidine
  - [x] M — Methionine
  - [x] C — Cysteine
- [x] Study alanine scanning.
- [x] Study BLOSUM62 conservative substitutions.
- [x] Study perturbation-based faithfulness testing.
- [x] Study SHAP and explanation faithfulness.
- [x] Study reliability evaluation beyond AUROC/MCC/accuracy.

### Deliverable
- Initial C3 literature review notes and verified references.

---

## Task 1.3 — Define the research problem and gap

### Subtasks
- [x] Document that existing AOP predictors are mainly evaluated using accuracy-oriented metrics.
- [x] Identify the lack of controlled physicochemical perturbation testing.
- [x] Identify the lack of a formal behavioural-consistency metric for AOP predictors.
- [x] Identify the gap between post-hoc explanation and actual prediction response.
- [x] Define how AOP-BCS addresses these gaps.

### Deliverable
- Finalized research problem and research gap.

---

## Research design workstream

## Task 2.1 — Finalize research objectives

### Subtasks
- [x] Finalize the main objective.
- [x] Finalize specific objectives:
  - [x] curate the audit dataset;
  - [x] develop the perturbation framework;
  - [x] audit multiple predictors;
  - [x] compute behavioural metrics;
  - [x] test SHAP faithfulness;
  - [x] compare behavioural reliability with conventional model performance.
- [x] Check that the objectives match the research gap.

### Deliverable
- Approved C3 objective set.

---

## Task 2.2 — Finalize research questions and hypotheses

### Subtasks
- [x] Finalize research questions concerning:
  - [x] conservative-edit invariance;
  - [x] redox-disruption sensitivity;
  - [x] BCS differences across predictors;
  - [x] SHAP faithfulness;
  - [x] relationship between BCS and conventional accuracy.
- [x] Finalize hypothesis pairs.
- [x] Define the statistical test associated with each hypothesis.
- [x] Keep the BCS-vs-AUROC comparison exploratory because of the small number of predictor-level observations.

### Deliverable
- Research-question and hypothesis table.

---

## Task 2.3 — Freeze the primary experimental protocol

### Subtasks
- [x] Freeze the redox-relevant set:

  `R_redox = {W, Y, H, M, C}`

- [x] Freeze sequence-length requirement:

  `3–50 amino acids`

- [x] Freeze the primary perturbation schemes:
  - [x] **P1:** Alanine scanning of redox residues.
  - [x] **P2:** BLOSUM62-conservative substitution at non-redox positions.
  - [x] **P3:** Random substitution control.
- [x] Freeze the P2 BLOSUM62 rule:
  - [x] score **>= +1**;
  - [x] exclude the original residue;
  - [x] exclude alanine;
  - [x] exclude members of `R_redox`;
  - [x] choose the highest-scoring eligible alternative.
- [x] Freeze the main threshold:

  `delta = 0.05`

- [x] Freeze sensitivity-analysis thresholds:

  `delta = {0.02, 0.05, 0.10}`

### Deliverable
- Versioned experimental protocol/configuration.

---

## Task 2.4 — Finalize evaluation metrics

### Subtasks
- [x] Define `DeltaScore` for every single-residue perturbation.
- [x] Define Prediction Flip Rate (PFR).
- [x] Define Invariance Rate (IR).
- [x] Define False Sensitivity Rate (FSR).
- [x] Define:

  `BCS = IR × (1 - FSR)`

- [x] Document interpretation:
  - [x] higher IR is better;
  - [x] lower FSR is better;
  - [x] higher BCS is better.
- [x] Define the later SHAP-faithfulness measure:

  `r(|SHAP_i|, |DeltaScore_i|)`

### Deliverable
- Final metric definitions.

---

## Task 2.5 — Finalize the methodology and validation plan

### Subtasks
- [x] Define the study as an in-silico computational experiment.
- [x] Define sequence validation rules.
- [x] Define perturbation validation rules.
- [x] Define predictor-score normalization requirements.
- [x] Define reproducibility requirements.
- [x] Define random-seed control.
- [x] Define caching/resume requirements for predictor scoring.
- [x] Define score/result schemas.
- [x] Define later statistical analysis:
  - [x] Kruskal-Wallis;
  - [x] Dunn post-hoc with Bonferroni correction;
  - [x] McNemar;
  - [x] one-tailed Wilcoxon;
  - [x] Pearson correlation;
  - [x] Fisher r-to-z;
  - [x] Shapiro-Wilk where relevant.

### Deliverable
- Final C3 methodology section.

---

## Task 2.6 — Complete proposal documentation

### Subtasks
- [x] Complete literature review.
- [x] Complete research gap.
- [x] Complete objectives.
- [x] Complete methodology.
- [x] Complete architecture.
- [x] Complete user requirements.
- [x] Complete functional requirements.
- [x] Complete non-functional requirements.
- [x] Complete commercialization plan.
- [x] Complete budget.
- [x] Complete WBS.
- [x] Complete Gantt chart.
- [x] Complete references.
- [x] Complete appendices.
- [x] Review the proposal with supervisors.
- [x] Submit/present the proposal.

### Deliverable
- Completed Component 3 proposal.

---

## Repository and environment workstream

## Task 3.1 — Prepare the team repository

### Subtasks
- [x] Clone the team GitHub repository.
- [x] Use the team `dev` branch as the base branch.
- [x] Create a Component 3 working branch, for example:

  `c3-aop-bcs`

- [x] Confirm the existing repository conventions before adding new files.
- [x] Create C3 folders following the team structure, for example:
  - [x] `src/plantaoX/c3_aop_bcs/`
  - [x] `tests/c3_aop_bcs/`
  - [x] `data/processed/c3_aop_bcs/`
- [x] Avoid duplicating root-level files that already exist.
- [x] Confirm `.venv/` and other temporary files are ignored by Git.

### Deliverable
- Clean C3 branch and repository structure.

---

## Task 3.2 — Prepare the Python environment

### Subtasks
- [x] Confirm the Python version used by the team.
- [x] Create/activate a virtual environment if required.
- [ ] Install the repository dependencies.
- [ ] Install C3-specific dependencies only if missing:
  - [x] pandas
  - [x] numpy
  - [x] scipy
  - [x] scikit-learn
  - [x] Biopython
  - [ ] PyYAML
  - [x] pytest
  - [ ] tqdm
  - [x] joblib
  - [ ] matplotlib
  - [ ] SHAP, if required for later preparation
- [ ] Confirm packages import correctly.
- [ ] Record package versions.

### Deliverable
- Reproducible local Python environment.

---

## Task 3.3 — Create the C3 research configuration

### Subtasks
- [x] Add configuration for:
  - [x] random seed;
  - [x] sequence minimum/maximum lengths;
  - [x] redox residues;
  - [x] CD-HIT threshold;
  - [x] primary delta;
  - [x] sensitivity deltas;
  - [x] pilot dataset size.
- [x] Create a configuration loader.
- [x] Test that the configuration loads correctly.
- [x] Avoid hard-coding research constants in many files.

### Deliverable
- Working C3 configuration file and loader.

---

# Phase 2 — Audit Dataset and Perturbation Pipeline

## Task 3.4 — Acquire the perturbation subject sequences

### Subtasks
- [x] Obtain the C3 audit sequences specified by the project design.
- [x] Prefer the E1/high-evidence AOP subject set where available.
- [x] Preserve the original source/provenance.
- [x] Store original files without manually editing them.
- [x] Record dataset version and acquisition date.

### Deliverable
- Raw/source audit sequences with provenance.

---

## Task 3.5 — Standardize sequence records

### Subtasks
- [x] Create a common data schema containing at least:
  - [x] sequence ID;
  - [x] peptide sequence;
  - [x] source;
  - [x] evidence/source information where available.
- [x] Convert sequences to uppercase.
- [x] Remove accidental whitespace.
- [x] Preserve the original source mapping.

### Deliverable
- Standardized intermediate dataset.

---

## Task 3.6 — Validate and clean sequences

### Subtasks
- [x] Reject missing sequences.
- [x] Reject invalid/non-standard amino-acid symbols.
- [x] Keep only standard peptide amino acids.
- [x] Enforce the 3–50 AA length range.
- [x] Remove exact duplicates.
- [x] Produce a cleaning report:
  - [x] original count;
  - [x] invalid count;
  - [x] out-of-range count;
  - [x] exact-duplicate count;
  - [x] retained count.

### Deliverable
- Validated and cleaned sequence dataset.

---

# Phase 3 — Dataset Finalization, Perturbation Engine, and Validation

## Task 3.7 — Apply 90% identity deduplication

### Subtasks
- [x] Convert cleaned sequences to FASTA.
- [x] Run CD-HIT at 90% identity.
- [x] Preserve the CD-HIT cluster output.
- [x] Convert representative sequences back to the working table format.
- [x] Record:
  - [x] input count;
  - [x] representative count;
  - [x] cluster count.

### Deliverable
- 90%-deduplicated audit dataset.

---

## Task 3.8 — Apply the redox-residue eligibility filter

### Subtasks
- [x] Detect whether each sequence contains at least one member of:

  `{W, Y, H, M, C}`

- [x] Keep eligible sequences for the primary P1 audit.
- [x] Record the number rejected because no redox residue is present.
- [x] Keep source/provenance information.

### Deliverable
- Final primary perturbation subject set for pilot testing.

---

## Task 3.9 — Annotate residue positions

### Subtasks
- [x] Number peptide positions from 1 to sequence length.
- [x] Record the residue at each position.
- [x] Mark each position as:
  - [x] redox;
  - [x] non-redox.
- [x] Store redox-position counts per peptide.
- [x] Export a residue-level annotation table.

### Deliverable
- Position-level residue annotation file.

---

## Perturbation engine workstream

## Task 3.10 — Define the perturbation output schema

### Subtasks
- [x] Store for every generated variant:
  - [x] sequence ID;
  - [x] original sequence;
  - [x] position;
  - [x] original residue;
  - [x] substituted residue;
  - [x] perturbed sequence;
  - [x] perturbation type;
  - [x] BLOSUM62 score where applicable;
  - [x] random seed/metadata where applicable.
- [x] Ensure one record corresponds to one one-position edit.

### Deliverable
- Frozen perturbation-data schema.

---

## Task 3.11 — Implement P1 alanine scanning

### Subtasks
- [x] Find every W/Y/H/M/C position.
- [x] Replace one redox residue at a time with alanine.
- [x] Preserve sequence length.
- [x] Generate one independent sequence per edited position.
- [x] Store mutation metadata.

### Required validation
- [x] exactly one position changed;
- [x] original residue belongs to `R_redox`;
- [x] replacement residue is `A`;
- [x] length does not change.

### Deliverable
- Working P1 generator.

---

## Task 3.12 — Implement BLOSUM62 support for P2

### Subtasks
- [x] Load the BLOSUM62 matrix using the selected library.
- [x] Create a function that evaluates candidate substitutions.
- [x] Exclude:
  - [x] the original amino acid;
  - [x] alanine;
  - [x] W/Y/H/M/C.
- [x] Keep only substitutions with BLOSUM62 score >= +1.
- [x] Select the highest-scoring eligible replacement.
- [x] Implement a deterministic tie-breaking rule.

### Deliverable
- Tested BLOSUM62 substitution-selection function.

---

## Task 3.13 — Implement P2 conservative substitutions

### Subtasks
- [x] Process only non-redox positions.
- [x] Apply the frozen BLOSUM62 selection rule.
- [x] Replace one position at a time.
- [x] Store the selected BLOSUM62 score.
- [x] Store mutation metadata.

### Required validation
- [x] exactly one position changed;
- [x] original position is non-redox;
- [x] new residue is not alanine;
- [x] new residue is not in `R_redox`;
- [x] BLOSUM62 score is >= +1;
- [x] sequence length is unchanged.

### Deliverable
- Working P2 generator.

---

## Task 3.14 — Implement P3 random-control substitutions

### Subtasks
- [x] Generate random valid single-residue substitutions.
- [x] Never replace a residue with itself.
- [x] Use a fixed master random seed.
- [x] Derive deterministic/reproducible random choices for each sequence/position.
- [x] Store random-control metadata.

### Required validation
- [x] exactly one position changed;
- [x] replacement is a valid amino acid;
- [x] replacement differs from the original;
- [x] sequence length is unchanged;
- [x] same input + same seed produces the same output.

### Deliverable
- Working P3 generator.

---

## Task 3.15 — Create a combined perturbation pipeline

### Subtasks
- [x] Accept the annotated peptide dataset as input.
- [x] Generate P1 variants.
- [x] Generate P2 variants.
- [x] Generate P3 variants.
- [x] Run automatic validation.
- [x] Reject invalid variants.
- [x] Export all accepted perturbations to CSV/Parquet/JSON as required by the repository.

### Deliverable
- End-to-end perturbation-generation pipeline.

---

## Automated validation workstream

## Task 3.16 — Create sequence-validation tests

### Subtasks
- [x] Test valid sequences.
- [x] Test invalid amino acids.
- [x] Test empty values.
- [x] Test minimum/maximum length rules.
- [x] Test duplicate handling.

### Deliverable
- Passing sequence-validation unit tests.

---

## Task 3.17 — Create P1/P2/P3 unit tests

### Subtasks
- [x] Test one-position-only changes.
- [x] Test P1 residue eligibility.
- [x] Test P1 alanine replacement.
- [x] Test P2 exclusion rules.
- [x] Test the BLOSUM62 >= +1 rule.
- [x] Test P2 deterministic selection.
- [x] Test P3 reproducibility.
- [x] Test unchanged sequence length.

### Deliverable
- Passing perturbation unit tests.

---

## Task 3.18 — Create reproducibility checks

### Subtasks
- [x] Run the same input twice using the same config.
- [x] Confirm identical perturbations.
- [x] Confirm identical random-control variants.
- [x] Record config/version/seed in each experimental run.

### Deliverable
- Reproducibility evidence for PP1.

---

# Phase 4 — Predictor Integration and Pilot Scoring

## Task 3.19 — Define the common predictor interface

### Subtasks
- [x] Define a common operation such as:

  `sequence -> predictor score`

- [x] Ensure every predictor adapter returns a consistent numeric result.
- [x] Design adapters so the rest of C3 does not depend on predictor architecture.
- [x] Define error handling for unavailable/failed scores.

### Deliverable
- Common predictor-adapter interface.

---

## Task 3.20 — Track predictor accessibility

### Subtasks
- [x] Check implementation/access status for:
  - [x] AnOxPePred
  - [x] Multi-AOP
  - [x] AOPxSVM
  - [x] AOP-DRL
  - [x] PU-AOP
- [x] Record:
  - [x] code/model availability;
  - [x] expected input format;
  - [x] output type;
  - [x] whether batch scoring is possible;
  - [x] license/access limitations;
  - [x] current integration status.
- [x] Do not claim a predictor is integrated until a real score has been verified.

### Deliverable
- Predictor-access/status table.

---

## Task 3.21 — Prioritize the minimum viable predictor set

### Subtasks
- [x] Prioritize:
  - [x] AnOxPePred;
  - [x] AOPxSVM;
  - [x] PU-AOP.
- [x] Coordinate with Component 2 for the PU-AOP frozen-model handoff.
- [x] Treat Multi-AOP and AOP-DRL as secondary if access/reproduction is not ready before PP1.
- [x] Document any unresolved access issue.

### Deliverable
- Realistic PP1 predictor-integration scope.

---

## Task 3.22 — Build a non-experimental dummy/smoke-test predictor

### Subtasks
- [x] Implement a simple deterministic scoring function only for pipeline testing.
- [x] Clearly label it as:
  - [x] software testing only;
  - [x] not a scientific AOP predictor;
  - [x] not part of experimental results.
- [x] Use it to verify the scoring/metric pipeline before real models are ready.

### Deliverable
- End-to-end software smoke-test capability.

---

## Task 3.23 — Implement predictor scoring

### Subtasks
- [x] Score each original peptide.
- [x] Score every P1/P2/P3 variant.
- [x] Cache original scores to avoid repeated calls.
- [x] Cache completed perturbed scores where allowed.
- [x] Add restart/resume behavior where practical.
- [x] Record predictor version and scoring method.

### Deliverable
- Original/perturbed score table for the pilot.

---

## Task 3.24 — Prepare score normalization

### Subtasks
- [x] Check each predictor's native output range.
- [x] Use native [0,1] probability scores where available.
- [x] Define/document any required score mapping for predictors that do not output probabilities.
- [x] Avoid batch-wise min-max scaling that would distort perturbation differences.
- [x] Confirm normalized/usable scores fall in the expected scale.

### Deliverable
- Comparable predictor-score representation.

---

## Pilot behavioural-metrics workstream

## Task 3.25 — Create the PP1 pilot subset

### Subtasks
- [x] Select a reproducible small subset of the audit dataset.
- [x] Use a fixed random seed.
- [x] Ensure multiple redox residues and sequence lengths are represented.
- [x] Use enough peptides to demonstrate the full workflow without running the final study.

### Suggested PP1 scale
- approximately 10–30 peptides, depending on scoring cost and predictor access.

### Deliverable
- Versioned pilot dataset.

---

# Phase 5 — Behavioural Metrics, Quality Control, and Reproducibility

## Task 3.26 — Calculate DeltaScore

### Subtasks
- [x] For each perturbation compute:

  `DeltaScore_i = Score(original) - Score(perturbed_i)`

- [x] Also store:

  `|DeltaScore_i|`

- [x] Verify calculations using hand-checked examples.

### Deliverable
- Per-position DeltaScore results.

---

## Task 3.27 — Detect prediction flips and calculate PFR

### Subtasks
- [x] Define/record the decision threshold used by each predictor.
- [x] Determine the original class.
- [x] Determine the perturbed class.
- [x] Record whether a flip occurs.
- [x] Compute PFR for the required groups.

### Deliverable
- Prediction-flip results.

---

## Task 3.28 — Calculate Invariance Rate (IR)

### Subtasks
- [x] Restrict the calculation to P2 variants.
- [x] Using the primary threshold `delta = 0.05`, mark a conservative edit invariant when:

  `|DeltaScore| < delta`

- [x] Calculate the fraction of invariant P2 edits.

### Deliverable
- Preliminary IR for each working pilot predictor.

---

## Task 3.29 — Calculate False Sensitivity Rate (FSR)

### Subtasks
- [x] Restrict the calculation to P1 variants.
- [x] Using `delta = 0.05`, mark insufficient response when:

  `|DeltaScore| < delta`

- [x] Calculate the fraction of P1 edits showing insufficient response.

### Deliverable
- Preliminary FSR for each working pilot predictor.

---

## Task 3.30 — Calculate preliminary BCS

### Subtasks
- [x] Compute:

  `BCS = IR × (1 - FSR)`

- [x] Check that BCS falls in the expected range.
- [x] Verify the formula with small manually calculated examples.
- [x] Report PP1 values as **preliminary pilot values**, not final conclusions.

### Deliverable
- Preliminary pilot BCS.

---

## Task 3.31 — Prepare delta-sensitivity support

### Subtasks
- [x] Ensure the metric code can accept:
  - [x] 0.02;
  - [x] 0.05;
  - [x] 0.10.
- [x] Use `0.05` as the primary PP1 result.
- [x] If time permits, demonstrate that the pipeline can rerun the other thresholds.
- [x] Leave the full robustness interpretation for the later study.

### Deliverable
- Configurable threshold-analysis code.

---

## Pilot quality and evidence workstream

## Task 3.32 — Review perturbation counts

### Subtasks
- [x] Count P1 variants.
- [x] Count P2 variants.
- [x] Count P3 variants.
- [x] Check for unexpected zero-variant cases.
- [x] Check whether any sequence dominates the generated dataset.

### Deliverable
- Perturbation summary table.

---

## Task 3.33 — Manually inspect example variants

### Subtasks
- [x] Select representative P1 examples.
- [x] Select representative P2 examples.
- [x] Select representative P3 examples.
- [x] Verify:
  - [x] mutation position;
  - [x] original/new residue;
  - [x] resulting sequence;
  - [x] BLOSUM62 score for P2;
  - [x] original and perturbed predictor scores.

### Deliverable
- Hand-verified examples for PP1 slides/demo.

---

## Task 3.34 — Create preliminary visualizations

### Subtasks
- [x] Create simple plots/tables such as:
  - [x] P1/P2/P3 `|DeltaScore|` distributions;
  - [x] original vs perturbed score examples;
  - [x] preliminary IR/FSR/BCS table;
  - [x] prediction-flip comparison.
- [x] Use only actual generated results.
- [x] Mark results as pilot/preliminary.

### Deliverable
- PP1-ready preliminary figures.

---

## Task 3.35 — Create run manifests and provenance records

### Subtasks
- [x] Record:
  - [x] dataset version;
  - [x] predictor version;
  - [x] code commit;
  - [x] random seed;
  - [x] redox set;
  - [x] BLOSUM62 rule;
  - [x] delta threshold;
  - [x] peptide count;
  - [x] perturbation counts;
  - [x] failures/missing scores;
  - [x] run date.
- [x] Keep result files versioned and traceable.

### Deliverable
- Reproducible run manifest.

---

## SHAP preparation workstream

## Task 3.36 — Prepare the SHAP-faithfulness data structure

### Subtasks
- [x] Define fields for:
  - [x] sequence ID;
  - [x] predictor;
  - [x] residue position;
  - [x] residue;
  - [x] SHAP value;
  - [x] absolute SHAP;
  - [x] P1 DeltaScore;
  - [x] absolute DeltaScore.
- [x] Confirm the later analysis will compare:

  `|SHAP_i|` vs `|DeltaScore_i|`

- [x] Prepare the code/module boundary for KernelSHAP.
- [x] Do not make the complete SHAP experiment a blocker for PP1.

### Deliverable
- SHAP-faithfulness implementation plan/schema.

---

# Phase 6 — PP1 Documentation, Evidence, and Delivery

## Task 3.37 — Update implementation documentation

### Subtasks
- [ ] Update the architecture diagram to match the real implementation.
- [ ] Document the actual repository structure.
- [ ] Document dataset-preparation steps.
- [ ] Document P1/P2/P3 rules.
- [ ] Document predictor-integration status.
- [ ] Document current limitations.
- [ ] Update README/configuration instructions.

### Deliverable
- Up-to-date implementation documentation.

---

## Task 3.38 — Maintain Git history

### Subtasks
- [x] Commit work in logical units.
- [x] Use clear commit messages, for example:
  - [x] `Initialize Component 3 AOP-BCS structure`
  - [x] `Add C3 research configuration`
  - [x] `Implement AOP sequence cleaning`
  - [x] `Add redox residue annotation`
  - [x] `Implement P1 alanine scanning`
  - [x] `Implement P2 BLOSUM62 substitutions`
  - [x] `Implement P3 random controls`
  - [x] `Add perturbation validation tests`
  - [ ] `Add behavioural metric calculations`
- [ ] Push the C3 branch regularly.
- [ ] Merge/update from `dev` using the team workflow.

### Deliverable
- Traceable implementation history.

---

## Task 3.39 — Update the research logbook

### Subtasks
Record major milestones rather than every minor coding action:
- [ ] repository/environment setup;
- [ ] dataset acquisition;
- [ ] cleaning and CD-HIT;
- [ ] residue annotation;
- [ ] P1 implementation;
- [ ] P2 implementation;
- [ ] P3 implementation;
- [ ] automated validation;
- [ ] predictor access investigation;
- [ ] predictor integration;
- [ ] pilot experiment;
- [ ] preliminary metrics;
- [ ] PP1 preparation;
- [ ] supervisor meetings and feedback.

### Deliverable
- Updated signed/verified logbook as required.

---

## Task 3.40 — Prepare PP1 evidence

### Subtasks
Capture evidence of:
- [ ] repository and branch;
- [ ] environment;
- [ ] raw/processed dataset;
- [ ] cleaning report;
- [ ] CD-HIT result;
- [ ] redox annotations;
- [ ] P1 variants;
- [ ] P2 variants;
- [ ] P3 variants;
- [ ] unit-test output;
- [ ] real predictor scoring;
- [ ] result table;
- [ ] DeltaScore;
- [ ] preliminary IR;
- [ ] preliminary FSR;
- [ ] preliminary BCS;
- [ ] figures;
- [ ] Git commits.

### Deliverable
- Organized PP1 evidence folder.

---

## Task 3.41 — Prepare the PP1 presentation

### Subtasks
- [ ] Add the component title.
- [ ] Explain the problem.
- [ ] Explain the research gap.
- [ ] Present the objective.
- [ ] Explain the AOP-BCS concept.
- [ ] Present the audit dataset.
- [ ] Present the fixed redox set.
- [ ] Explain the P1/P2/P3 methodology.
- [ ] Present the implemented architecture.
- [ ] Present dataset-preparation progress.
- [ ] Present perturbation-engine progress.
- [ ] Present predictor-integration status.
- [ ] Present the pilot experiment.
- [ ] Present preliminary DeltaScore/PFR/IR/FSR/BCS results.
- [ ] Present validation and reproducibility evidence.
- [ ] Explain challenges and unresolved dependencies.
- [ ] Present work planned after PP1.

### Deliverable
- Final PP1 slide deck and speaking notes.

---

## Task 3.42 — PP1 rehearsal and final verification

### Subtasks
- [ ] Run the pilot pipeline again from a clean configuration.
- [ ] Confirm generated files are reproducible.
- [ ] Confirm all unit tests pass.
- [ ] Confirm presentation figures match the latest result files.
- [ ] Confirm no dummy predictor result is presented as scientific evidence.
- [ ] Confirm predictor-access limitations are stated accurately.
- [ ] Practice explaining:
  - [ ] why C3 is an audit rather than a classifier;
  - [ ] why W/Y/H/M/C were fixed;
  - [ ] why P1, P2 and P3 are needed;
  - [ ] why P2 uses BLOSUM62 >= +1;
  - [ ] what IR means;
  - [ ] what FSR means;
  - [ ] why `BCS = IR × (1 - FSR)`;
  - [ ] what remains after PP1.

### Deliverable
- PP1-ready Component 3 implementation and presentation.

---

## Task 3.43 — Build the AOP-BCS progress-presentation frontend

### Subtasks
- [x] Review the shared frontend structure, navigation, card, badge, typography, spacing, colour, and responsive-layout patterns without modifying other components.
- [x] Review the C3 task/status records and authoritative PP1 artifacts before defining the presentation content.
- [x] Create a standalone responsive frontend entirely under `src/plantaox/c3_aop_bcs/frontend/`.
- [x] Present the research problem, AOP-BCS concept, dataset pipeline, P1/P2/P3 methodology, pilot metrics, predictor readiness, limitations, and next work as a coherent presentation narrative.
- [x] Populate the interface only from versioned C3 evidence and clearly label every dummy-predictor value as software-testing-only and non-scientific.
- [x] Add an interactive real-artifact perturbation explorer and accessible presentation navigation.
- [x] Match the established PlantAOx design language while keeping the C3 frontend visually distinctive and presentation-ready.
- [x] Add local launch instructions and automated checks for content integrity and scope safety.
- [x] Validate desktop and mobile layouts and confirm no files outside `c3_aop_bcs` were changed.

### Deliverable
- Presentation-ready standalone AOP-BCS frontend backed by the versioned PP1 artifacts.

---

## Task 3.44 — Align the AOP-BCS frontend with the shared research dashboard

### Subtasks
- [x] Re-audit the shared application shell, component navigation, cards, badges, stat tiles, tables, charts, explorer controls, provenance, and limitation patterns without modifying them.
- [x] Replace the presentation-oriented one-page layout with the same compact dashboard shell used by the other components.
- [x] Add component-level dashboard views for overview, dataset, perturbations, pilot metrics, variant explorer, predictor status, and evidence.
- [x] Reuse the shared PlantAOx colour tokens, typography scale, spacing, card treatment, responsive breakpoints, and light/dark behavior.
- [x] Preserve the generated C3 evidence adapter and populate every dashboard view only from versioned C3 artifacts.
- [x] Keep dummy-predictor results visibly labelled as software-testing-only and non-scientific in every relevant view.
- [x] Update automated checks and local instructions for the dashboard navigation and content structure.
- [x] Validate dashboard interactions and responsive layouts and confirm no file outside `c3_aop_bcs` changed.

### Deliverable
- Standalone AOP-BCS research dashboard matching the established Component 1, 2, and 4 frontend patterns.

---

## Task 3.45 — Connect the AOP-BCS dashboard to a C3 backend

### Subtasks
- [x] Re-read the C3 task/status records and audit the shared FastAPI conventions without modifying shared or other-component files.
- [x] Create a C3-owned FastAPI application with health and dashboard-data endpoints under `/api/v1/c3`.
- [x] Load dashboard responses from the authoritative versioned C3 artifacts and validate required evidence before responding.
- [x] Serve the C3 dashboard and its generated figures from the same backend process so local use requires one command and no CORS workaround.
- [x] Replace the frontend's static snapshot dependency with the C3 dashboard API and add visible loading/error/backend-status states.
- [x] Add focused backend/API and frontend contract tests, including missing-artifact failure behavior and scientific-boundary checks.
- [x] Update the C3 frontend run instructions and document the shared-router integration boundary imposed by the component-only edit scope.
- [x] Run automated tests and browser verification, then confirm that no file outside `c3_aop_bcs` changed.

### Deliverable
- A locally runnable AOP-BCS dashboard backed by live, validated C3 artifact APIs, entirely contained within `src/plantaox/c3_aop_bcs/`.

---

## Task 3.46 — Rebuild the C3 frontend using the shared React application structure

### Subtasks
- [x] Re-audit the shared React/Vite architecture, routes, component registry, UI primitives, API client, data-state handling, styling tokens, tests, and startup workflow without modifying shared files.
- [ ] Replace the standalone plain-JavaScript page with a React 19, TypeScript, Vite, Tailwind CSS, and React Router application inside `c3_aop_bcs/frontend`.
- [ ] Mirror the shared directory structure: `app`, `components/layout`, `components/ui`, `components/research`, `features/c3-aop-bcs`, `lib/api`, and `styles`.
- [ ] Split Overview, Dataset, Perturbations, Pilot metrics, Variant explorer, Predictors, and Evidence into typed route-level pages.
- [ ] Reuse shared-style Card, Badge, StatTile, DataState, LimitationsPanel, header, sidebar, and component-nav patterns.
- [ ] Connect typed C3 services to `/api/v1/c3` and preserve loading, unavailable, and error states.
- [ ] Preserve every software-testing-only warning and prevent dummy outputs from being presented as scientific evidence.
- [ ] Add component/API/router tests, production build validation, and a one-command C3 frontend/backend development launcher.
- [ ] Verify the responsive application in the browser and confirm no file outside a `c3_aop_bcs` path changed.

### Deliverable
- A typed, tested AOP-BCS React dashboard following the same structure and behavior conventions as the shared PlantAOx frontend while remaining inside the authorized C3 scope.

---

# PP1 Quality Gate

Before considering the PP1 implementation stage complete, verify the following.

## Must be working by PP1
- [x] Team repository cloned and C3 branch created.
- [ ] C3 environment/configuration works.
- [x] Audit sequences acquired.
- [x] Sequences standardized and validated.
- [x] 3–50 AA filter applied.
- [x] 90% CD-HIT deduplication completed or demonstrably working on the intended dataset.
- [x] Redox filter `{W,Y,H,M,C}` applied.
- [x] Residue annotation works.
- [x] P1 generator works.
- [x] P2 generator works using BLOSUM62 >= +1.
- [x] P3 random-control generator works.
- [x] One-position mutation validation works.
- [x] Automated tests pass.
- [x] Common predictor interface exists.
- [x] Predictor-access status is documented.
- [ ] At least one real predictor has been successfully scored if technically accessible.
- [ ] Pilot original/perturbed scores are stored.
- [ ] DeltaScore is computed.
- [ ] Prediction flips are computed.
- [ ] IR is computed.
- [ ] FSR is computed.
- [ ] Preliminary BCS is computed.
- [x] Run configuration/seed/version information is recorded.
- [ ] PP1 evidence and screenshots are prepared.
- [ ] PP1 slides are prepared.

---

# Work That Can Continue After PP1

The following are part of the full proposal but do **not** need to block PP1 if the working pilot pipeline is already demonstrated:

- complete scoring across all five target predictors;
- full audit across the final 150–400+ subject set;
- full delta sensitivity interpretation at 0.02/0.05/0.10;
- complete HP1–HP5 statistical testing;
- full KernelSHAP experiment;
- Pearson SHAP-faithfulness results;
- Fisher r-to-z cross-model comparison;
- complete BCS-vs-AUROC exploratory analysis;
- final HIGH/LOW predictor reliability flag;
- final predictor comparison/leaderboard;
- final Component 4 handoff;
- final dissertation/paper analysis.

---

# Recommended Implementation Order

Use this order to avoid building later steps on unvalidated inputs:

1. Clone repository and create C3 branch.
2. Inspect existing team project structure.
3. Prepare environment.
4. Create C3 configuration.
5. Acquire audit dataset.
6. Standardize sequence records.
7. Clean and validate sequences.
8. Apply 3–50 AA filter.
9. Remove exact duplicates.
10. Run CD-HIT at 90%.
11. Apply redox-residue filter.
12. Annotate residue positions.
13. Freeze perturbation schema.
14. Implement P1.
15. Test/validate P1.
16. Load and test BLOSUM62.
17. Implement P2.
18. Test/validate P2.
19. Implement P3.
20. Test P3 reproducibility.
21. Build combined perturbation pipeline.
22. Add automated tests.
23. Create reproducible pilot subset.
24. Define common predictor interface.
25. Track predictor access.
26. Test the software pipeline with a clearly labelled dummy predictor.
27. Integrate the first real predictor.
28. Integrate additional feasible predictor(s).
29. Add score caching/resume support.
30. Normalize/standardize predictor outputs as required.
31. Calculate DeltaScore.
32. Detect prediction flips.
33. Calculate IR.
34. Calculate FSR.
35. Calculate preliminary BCS.
36. Confirm delta is configurable.
37. Manually inspect example perturbations.
38. Export pilot results.
39. Generate preliminary plots/tables.
40. Create run manifest/provenance record.
41. Update implementation documentation.
42. Update logbook.
43. Prepare PP1 evidence.
44. Prepare PP1 slides.
45. Run final end-to-end PP1 rehearsal.

---

# Expected PP1 Demonstration

By PP1, the strongest demonstration is:

```text
Validated AOP subject set
        ↓
Redox annotation
        ↓
P1 / P2 / P3 generation
        ↓
Automatic perturbation validation
        ↓
Available AOP predictor(s)
        ↓
Original and perturbed scores
        ↓
DeltaScore + prediction flips
        ↓
Preliminary IR + FSR
        ↓
Preliminary BCS
        ↓
Reproducible pilot results
```

gitA concise explanation for PP1 is:

> “I have implemented the core AOP-BCS behavioural-audit pipeline. The system prepares a validated AOP subject set, identifies the fixed W/Y/H/M/C redox positions, generates and validates P1, P2 and P3 one-position perturbations, sends original and perturbed sequences through available AOP predictors, records score changes and prediction flips, and calculates preliminary IR, FSR and BCS values. The full five-predictor experiment, statistical hypothesis testing and SHAP-faithfulness analysis continue after PP1.”

