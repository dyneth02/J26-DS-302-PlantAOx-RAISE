# Component 3 (AOP-BCS) — Work Plan Up to Progress Presentation 1 (PP1)

**Component:** Component 3 — AOP-BCS  
**Title:** *Physicochemical Faithfulness Audit for Antioxidant Peptide Predictors via Controlled Sequence Perturbation Benchmarking*  
**Project:** PlantAOx-RAISE  
**Scope of this plan:** Work to be completed from the beginning of the project up to **Progress Presentation 1 (PP1)**.

> This task plan is derived from the Component 3 proposal report, especially the objectives, methodology, validation strategy, functional/non-functional requirements, development phases, WBS/Gantt structure, and the C3 task definition.  
> The PP1 implementation target is a **working and validated pilot audit pipeline**, not the complete final multi-predictor statistical/SHAP study.

---

# Phase 1 — Research Definition and Project Foundation

## [x] Task 1.1 — Confirm Component 3 responsibility

### Subtasks
- Confirm Component 3 research title: **AOP-BCS**.
- Confirm the individual responsibility boundary of Component 3.
- Confirm how C3 connects to:
  - Component 2: receives the PU-AOP predictor for auditing.
  - Component 4: provides predictor-level reliability evidence.
- Confirm that C3 is an **audit framework**, not a new AOP classifier.
- Record the component scope in the project documentation and logbook.

### Deliverable
- Confirmed C3 scope and responsibility statement.

---

## [x] Task 1.2 — Initial literature study

### Subtasks
- Study existing AOP predictors:
  - AnOxPePred
  - Multi-AOP
  - AOPxSVM
  - AOP-DRL
  - PU-AOP from Component 2
- Study antioxidant-relevant amino-acid chemistry.
- Study evidence supporting the fixed redox residue set:
  - W — Tryptophan
  - Y — Tyrosine
  - H — Histidine
  - M — Methionine
  - C — Cysteine
- Study alanine scanning.
- Study BLOSUM62 conservative substitutions.
- Study perturbation-based faithfulness testing.
- Study SHAP and explanation faithfulness.
- Study reliability evaluation beyond AUROC/MCC/accuracy.

### Deliverable
- Initial C3 literature review notes and verified references.

---

## [x] Task 1.3 — Define the research problem and gap

### Subtasks
- Document that existing AOP predictors are mainly evaluated using accuracy-oriented metrics.
- Identify the lack of controlled physicochemical perturbation testing.
- Identify the lack of a formal behavioural-consistency metric for AOP predictors.
- Identify the gap between post-hoc explanation and actual prediction response.
- Define how AOP-BCS addresses these gaps.

### Deliverable
- Finalized research problem and research gap.

---

## Research design workstream

## [x] Task 2.1 — Finalize research objectives

### Subtasks
- Finalize the main objective.
- Finalize specific objectives:
  - curate the audit dataset;
  - develop the perturbation framework;
  - audit multiple predictors;
  - compute behavioural metrics;
  - test SHAP faithfulness;
  - compare behavioural reliability with conventional model performance.
- Check that the objectives match the research gap.

### Deliverable
- Approved C3 objective set.

---

## [x] Task 2.2 — Finalize research questions and hypotheses

### Subtasks
- Finalize research questions concerning:
  - conservative-edit invariance;
  - redox-disruption sensitivity;
  - BCS differences across predictors;
  - SHAP faithfulness;
  - relationship between BCS and conventional accuracy.
- Finalize hypothesis pairs.
- Define the statistical test associated with each hypothesis.
- Keep the BCS-vs-AUROC comparison exploratory because of the small number of predictor-level observations.

### Deliverable
- Research-question and hypothesis table.

---

## [x] Task 2.3 — Freeze the primary experimental protocol

### Subtasks
- Freeze the redox-relevant set:

  `R_redox = {W, Y, H, M, C}`

- Freeze sequence-length requirement:

  `3–50 amino acids`

- Freeze the primary perturbation schemes:
  - **P1:** Alanine scanning of redox residues.
  - **P2:** BLOSUM62-conservative substitution at non-redox positions.
  - **P3:** Random substitution control.
- Freeze the P2 BLOSUM62 rule:
  - score **>= +1**;
  - exclude the original residue;
  - exclude alanine;
  - exclude members of `R_redox`;
  - choose the highest-scoring eligible alternative.
- Freeze the main threshold:

  `delta = 0.05`

- Freeze sensitivity-analysis thresholds:

  `delta = {0.02, 0.05, 0.10}`

### Deliverable
- Versioned experimental protocol/configuration.

---

## [x] Task 2.4 — Finalize evaluation metrics

### Subtasks
- Define `DeltaScore` for every single-residue perturbation.
- Define Prediction Flip Rate (PFR).
- Define Invariance Rate (IR).
- Define False Sensitivity Rate (FSR).
- Define:

  `BCS = IR × (1 - FSR)`

- Document interpretation:
  - higher IR is better;
  - lower FSR is better;
  - higher BCS is better.
- Define the later SHAP-faithfulness measure:

  `r(|SHAP_i|, |DeltaScore_i|)`

### Deliverable
- Final metric definitions.

---

## [x] Task 2.5 — Finalize the methodology and validation plan

### Subtasks
- Define the study as an in-silico computational experiment.
- Define sequence validation rules.
- Define perturbation validation rules.
- Define predictor-score normalization requirements.
- Define reproducibility requirements.
- Define random-seed control.
- Define caching/resume requirements for predictor scoring.
- Define score/result schemas.
- Define later statistical analysis:
  - Kruskal-Wallis;
  - Dunn post-hoc with Bonferroni correction;
  - McNemar;
  - one-tailed Wilcoxon;
  - Pearson correlation;
  - Fisher r-to-z;
  - Shapiro-Wilk where relevant.

### Deliverable
- Final C3 methodology section.

---

## [x] Task 2.6 — Complete proposal documentation

### Subtasks
- Complete literature review.
- Complete research gap.
- Complete objectives.
- Complete methodology.
- Complete architecture.
- Complete user requirements.
- Complete functional requirements.
- Complete non-functional requirements.
- Complete commercialization plan.
- Complete budget.
- Complete WBS.
- Complete Gantt chart.
- Complete references.
- Complete appendices.
- Review the proposal with supervisors.
- Submit/present the proposal.

### Deliverable
- Completed Component 3 proposal.

---

## Repository and environment workstream

## [x] Task 3.1 — Prepare the team repository

### Subtasks
- Clone the team GitHub repository.
- Use the team `dev` branch as the base branch.
- Create a Component 3 working branch, for example:

  `c3-aop-bcs`

- Confirm the existing repository conventions before adding new files.
- Create C3 folders following the team structure, for example:
  - `src/plantaoX/c3_aop_bcs/`
  - `tests/c3_aop_bcs/`
  - `data/processed/c3_aop_bcs/`
- Avoid duplicating root-level files that already exist.
- Confirm `.venv/` and other temporary files are ignored by Git.

### Deliverable
- Clean C3 branch and repository structure.

---

## [ ] Task 3.2 — Prepare the Python environment

### Subtasks
- Confirm the Python version used by the team.
- Create/activate a virtual environment if required.
- Install the repository dependencies.
- Install C3-specific dependencies only if missing:
  - pandas
  - numpy
  - scipy
  - scikit-learn
  - Biopython
  - PyYAML
  - pytest
  - tqdm
  - joblib
  - matplotlib
  - SHAP, if required for later preparation
- Confirm packages import correctly.
- Record package versions.

### Deliverable
- Reproducible local Python environment.

---

## [x] Task 3.3 — Create the C3 research configuration

### Subtasks
- Add configuration for:
  - random seed;
  - sequence minimum/maximum lengths;
  - redox residues;
  - CD-HIT threshold;
  - primary delta;
  - sensitivity deltas;
  - pilot dataset size.
- Create a configuration loader.
- Test that the configuration loads correctly.
- Avoid hard-coding research constants in many files.

### Deliverable
- Working C3 configuration file and loader.

---

# Phase 2 — Audit Dataset and Perturbation Pipeline

## [x] Task 3.4 — Acquire the perturbation subject sequences

### Subtasks
- Obtain the C3 audit sequences specified by the project design.
- Prefer the E1/high-evidence AOP subject set where available.
- Preserve the original source/provenance.
- Store original files without manually editing them.
- Record dataset version and acquisition date.

### Deliverable
- Raw/source audit sequences with provenance.

---

## [x] Task 3.5 — Standardize sequence records

### Subtasks
- Create a common data schema containing at least:
  - sequence ID;
  - peptide sequence;
  - source;
  - evidence/source information where available.
- Convert sequences to uppercase.
- Remove accidental whitespace.
- Preserve the original source mapping.

### Deliverable
- Standardized intermediate dataset.

---

## [x] Task 3.6 — Validate and clean sequences

### Subtasks
- Reject missing sequences.
- Reject invalid/non-standard amino-acid symbols.
- Keep only standard peptide amino acids.
- Enforce the 3–50 AA length range.
- Remove exact duplicates.
- Produce a cleaning report:
  - original count;
  - invalid count;
  - out-of-range count;
  - exact-duplicate count;
  - retained count.

### Deliverable
- Validated and cleaned sequence dataset.

---

## [ ] Task 3.7 — Apply 90% identity deduplication

### Subtasks
- Convert cleaned sequences to FASTA.
- Run CD-HIT at 90% identity.
- Preserve the CD-HIT cluster output.
- Convert representative sequences back to the working table format.
- Record:
  - input count;
  - representative count;
  - cluster count.

### Deliverable
- 90%-deduplicated audit dataset.

---

## [ ] Task 3.8 — Apply the redox-residue eligibility filter

### Subtasks
- Detect whether each sequence contains at least one member of:

  `{W, Y, H, M, C}`

- Keep eligible sequences for the primary P1 audit.
- Record the number rejected because no redox residue is present.
- Keep source/provenance information.

### Deliverable
- Final primary perturbation subject set for pilot testing.

---

## [ ] Task 3.9 — Annotate residue positions

### Subtasks
- Number peptide positions from 1 to sequence length.
- Record the residue at each position.
- Mark each position as:
  - redox;
  - non-redox.
- Store redox-position counts per peptide.
- Export a residue-level annotation table.

### Deliverable
- Position-level residue annotation file.

---

## Perturbation engine workstream

## [ ] Task 3.10 — Define the perturbation output schema

### Subtasks
- Store for every generated variant:
  - sequence ID;
  - original sequence;
  - position;
  - original residue;
  - substituted residue;
  - perturbed sequence;
  - perturbation type;
  - BLOSUM62 score where applicable;
  - random seed/metadata where applicable.
- Ensure one record corresponds to one one-position edit.

### Deliverable
- Frozen perturbation-data schema.

---

## [ ] Task 3.11 — Implement P1 alanine scanning

### Subtasks
- Find every W/Y/H/M/C position.
- Replace one redox residue at a time with alanine.
- Preserve sequence length.
- Generate one independent sequence per edited position.
- Store mutation metadata.

### Required validation
- exactly one position changed;
- original residue belongs to `R_redox`;
- replacement residue is `A`;
- length does not change.

### Deliverable
- Working P1 generator.

---

## [ ] Task 3.12 — Implement BLOSUM62 support for P2

### Subtasks
- Load the BLOSUM62 matrix using the selected library.
- Create a function that evaluates candidate substitutions.
- Exclude:
  - the original amino acid;
  - alanine;
  - W/Y/H/M/C.
- Keep only substitutions with BLOSUM62 score >= +1.
- Select the highest-scoring eligible replacement.
- Implement a deterministic tie-breaking rule.

### Deliverable
- Tested BLOSUM62 substitution-selection function.

---

## [ ] Task 3.13 — Implement P2 conservative substitutions

### Subtasks
- Process only non-redox positions.
- Apply the frozen BLOSUM62 selection rule.
- Replace one position at a time.
- Store the selected BLOSUM62 score.
- Store mutation metadata.

### Required validation
- exactly one position changed;
- original position is non-redox;
- new residue is not alanine;
- new residue is not in `R_redox`;
- BLOSUM62 score is >= +1;
- sequence length is unchanged.

### Deliverable
- Working P2 generator.

---

## [ ] Task 3.14 — Implement P3 random-control substitutions

### Subtasks
- Generate random valid single-residue substitutions.
- Never replace a residue with itself.
- Use a fixed master random seed.
- Derive deterministic/reproducible random choices for each sequence/position.
- Store random-control metadata.

### Required validation
- exactly one position changed;
- replacement is a valid amino acid;
- replacement differs from the original;
- sequence length is unchanged;
- same input + same seed produces the same output.

### Deliverable
- Working P3 generator.

---

## [ ] Task 3.15 — Create a combined perturbation pipeline

### Subtasks
- Accept the annotated peptide dataset as input.
- Generate P1 variants.
- Generate P2 variants.
- Generate P3 variants.
- Run automatic validation.
- Reject invalid variants.
- Export all accepted perturbations to CSV/Parquet/JSON as required by the repository.

### Deliverable
- End-to-end perturbation-generation pipeline.

---

## Automated validation workstream

## [ ] Task 3.16 — Create sequence-validation tests

### Subtasks
- Test valid sequences.
- Test invalid amino acids.
- Test empty values.
- Test minimum/maximum length rules.
- Test duplicate handling.

### Deliverable
- Passing sequence-validation unit tests.

---

## [ ] Task 3.17 — Create P1/P2/P3 unit tests

### Subtasks
- Test one-position-only changes.
- Test P1 residue eligibility.
- Test P1 alanine replacement.
- Test P2 exclusion rules.
- Test the BLOSUM62 >= +1 rule.
- Test P2 deterministic selection.
- Test P3 reproducibility.
- Test unchanged sequence length.

### Deliverable
- Passing perturbation unit tests.

---

## [ ] Task 3.18 — Create reproducibility checks

### Subtasks
- Run the same input twice using the same config.
- Confirm identical perturbations.
- Confirm identical random-control variants.
- Record config/version/seed in each experimental run.

### Deliverable
- Reproducibility evidence for PP1.

---

# Phase 3 — Predictor Integration, Pilot Evaluation, and PP1 Delivery

## [ ] Task 3.19 — Define the common predictor interface

### Subtasks
- Define a common operation such as:

  `sequence -> predictor score`

- Ensure every predictor adapter returns a consistent numeric result.
- Design adapters so the rest of C3 does not depend on predictor architecture.
- Define error handling for unavailable/failed scores.

### Deliverable
- Common predictor-adapter interface.

---

## [ ] Task 3.20 — Track predictor accessibility

### Subtasks
- Check implementation/access status for:
  - AnOxPePred
  - Multi-AOP
  - AOPxSVM
  - AOP-DRL
  - PU-AOP
- Record:
  - code/model availability;
  - expected input format;
  - output type;
  - whether batch scoring is possible;
  - license/access limitations;
  - current integration status.
- Do not claim a predictor is integrated until a real score has been verified.

### Deliverable
- Predictor-access/status table.

---

## [ ] Task 3.21 — Prioritize the minimum viable predictor set

### Subtasks
- Prioritize:
  - AnOxPePred;
  - AOPxSVM;
  - PU-AOP.
- Coordinate with Component 2 for the PU-AOP frozen-model handoff.
- Treat Multi-AOP and AOP-DRL as secondary if access/reproduction is not ready before PP1.
- Document any unresolved access issue.

### Deliverable
- Realistic PP1 predictor-integration scope.

---

## [ ] Task 3.22 — Build a non-experimental dummy/smoke-test predictor

### Subtasks
- Implement a simple deterministic scoring function only for pipeline testing.
- Clearly label it as:
  - software testing only;
  - not a scientific AOP predictor;
  - not part of experimental results.
- Use it to verify the scoring/metric pipeline before real models are ready.

### Deliverable
- End-to-end software smoke-test capability.

---

## [ ] Task 3.23 — Implement predictor scoring

### Subtasks
- Score each original peptide.
- Score every P1/P2/P3 variant.
- Cache original scores to avoid repeated calls.
- Cache completed perturbed scores where allowed.
- Add restart/resume behavior where practical.
- Record predictor version and scoring method.

### Deliverable
- Original/perturbed score table for the pilot.

---

## [ ] Task 3.24 — Prepare score normalization

### Subtasks
- Check each predictor's native output range.
- Use native [0,1] probability scores where available.
- Define/document any required score mapping for predictors that do not output probabilities.
- Avoid batch-wise min-max scaling that would distort perturbation differences.
- Confirm normalized/usable scores fall in the expected scale.

### Deliverable
- Comparable predictor-score representation.

---

## Pilot behavioural-metrics workstream

## [ ] Task 3.25 — Create the PP1 pilot subset

### Subtasks
- Select a reproducible small subset of the audit dataset.
- Use a fixed random seed.
- Ensure multiple redox residues and sequence lengths are represented.
- Use enough peptides to demonstrate the full workflow without running the final study.

### Suggested PP1 scale
- approximately 10–30 peptides, depending on scoring cost and predictor access.

### Deliverable
- Versioned pilot dataset.

---

## [ ] Task 3.26 — Calculate DeltaScore

### Subtasks
- For each perturbation compute:

  `DeltaScore_i = Score(original) - Score(perturbed_i)`

- Also store:

  `|DeltaScore_i|`

- Verify calculations using hand-checked examples.

### Deliverable
- Per-position DeltaScore results.

---

## [ ] Task 3.27 — Detect prediction flips and calculate PFR

### Subtasks
- Define/record the decision threshold used by each predictor.
- Determine the original class.
- Determine the perturbed class.
- Record whether a flip occurs.
- Compute PFR for the required groups.

### Deliverable
- Prediction-flip results.

---

## [ ] Task 3.28 — Calculate Invariance Rate (IR)

### Subtasks
- Restrict the calculation to P2 variants.
- Using the primary threshold `delta = 0.05`, mark a conservative edit invariant when:

  `|DeltaScore| < delta`

- Calculate the fraction of invariant P2 edits.

### Deliverable
- Preliminary IR for each working pilot predictor.

---

## [ ] Task 3.29 — Calculate False Sensitivity Rate (FSR)

### Subtasks
- Restrict the calculation to P1 variants.
- Using `delta = 0.05`, mark insufficient response when:

  `|DeltaScore| < delta`

- Calculate the fraction of P1 edits showing insufficient response.

### Deliverable
- Preliminary FSR for each working pilot predictor.

---

## [ ] Task 3.30 — Calculate preliminary BCS

### Subtasks
- Compute:

  `BCS = IR × (1 - FSR)`

- Check that BCS falls in the expected range.
- Verify the formula with small manually calculated examples.
- Report PP1 values as **preliminary pilot values**, not final conclusions.

### Deliverable
- Preliminary pilot BCS.

---

## [ ] Task 3.31 — Prepare delta-sensitivity support

### Subtasks
- Ensure the metric code can accept:
  - 0.02;
  - 0.05;
  - 0.10.
- Use `0.05` as the primary PP1 result.
- If time permits, demonstrate that the pipeline can rerun the other thresholds.
- Leave the full robustness interpretation for the later study.

### Deliverable
- Configurable threshold-analysis code.

---

## Pilot quality and evidence workstream

## [ ] Task 3.32 — Review perturbation counts

### Subtasks
- Count P1 variants.
- Count P2 variants.
- Count P3 variants.
- Check for unexpected zero-variant cases.
- Check whether any sequence dominates the generated dataset.

### Deliverable
- Perturbation summary table.

---

## [ ] Task 3.33 — Manually inspect example variants

### Subtasks
- Select representative P1 examples.
- Select representative P2 examples.
- Select representative P3 examples.
- Verify:
  - mutation position;
  - original/new residue;
  - resulting sequence;
  - BLOSUM62 score for P2;
  - original and perturbed predictor scores.

### Deliverable
- Hand-verified examples for PP1 slides/demo.

---

## [ ] Task 3.34 — Create preliminary visualizations

### Subtasks
- Create simple plots/tables such as:
  - P1/P2/P3 `|DeltaScore|` distributions;
  - original vs perturbed score examples;
  - preliminary IR/FSR/BCS table;
  - prediction-flip comparison.
- Use only actual generated results.
- Mark results as pilot/preliminary.

### Deliverable
- PP1-ready preliminary figures.

---

## [ ] Task 3.35 — Create run manifests and provenance records

### Subtasks
- Record:
  - dataset version;
  - predictor version;
  - code commit;
  - random seed;
  - redox set;
  - BLOSUM62 rule;
  - delta threshold;
  - peptide count;
  - perturbation counts;
  - failures/missing scores;
  - run date.
- Keep result files versioned and traceable.

### Deliverable
- Reproducible run manifest.

---

## SHAP preparation workstream

## [ ] Task 3.36 — Prepare the SHAP-faithfulness data structure

### Subtasks
- Define fields for:
  - sequence ID;
  - predictor;
  - residue position;
  - residue;
  - SHAP value;
  - absolute SHAP;
  - P1 DeltaScore;
  - absolute DeltaScore.
- Confirm the later analysis will compare:

  `|SHAP_i|` vs `|DeltaScore_i|`

- Prepare the code/module boundary for KernelSHAP.
- Do not make the complete SHAP experiment a blocker for PP1.

### Deliverable
- SHAP-faithfulness implementation plan/schema.

---

## PP1 documentation and presentation workstream

## [ ] Task 3.37 — Update implementation documentation

### Subtasks
- Update the architecture diagram to match the real implementation.
- Document the actual repository structure.
- Document dataset-preparation steps.
- Document P1/P2/P3 rules.
- Document predictor-integration status.
- Document current limitations.
- Update README/configuration instructions.

### Deliverable
- Up-to-date implementation documentation.

---

## [ ] Task 3.38 — Maintain Git history

### Subtasks
- Commit work in logical units.
- Use clear commit messages, for example:
  - `Initialize Component 3 AOP-BCS structure`
  - `Add C3 research configuration`
  - `Implement AOP sequence cleaning`
  - `Add redox residue annotation`
  - `Implement P1 alanine scanning`
  - `Implement P2 BLOSUM62 substitutions`
  - `Implement P3 random controls`
  - `Add perturbation validation tests`
  - `Add behavioural metric calculations`
- Push the C3 branch regularly.
- Merge/update from `dev` using the team workflow.

### Deliverable
- Traceable implementation history.

---

## [ ] Task 3.39 — Update the research logbook

### Subtasks
Record major milestones rather than every minor coding action:
- repository/environment setup;
- dataset acquisition;
- cleaning and CD-HIT;
- residue annotation;
- P1 implementation;
- P2 implementation;
- P3 implementation;
- automated validation;
- predictor access investigation;
- predictor integration;
- pilot experiment;
- preliminary metrics;
- PP1 preparation;
- supervisor meetings and feedback.

### Deliverable
- Updated signed/verified logbook as required.

---

## [ ] Task 3.40 — Prepare PP1 evidence

### Subtasks
Capture evidence of:
- repository and branch;
- environment;
- raw/processed dataset;
- cleaning report;
- CD-HIT result;
- redox annotations;
- P1 variants;
- P2 variants;
- P3 variants;
- unit-test output;
- real predictor scoring;
- result table;
- DeltaScore;
- preliminary IR;
- preliminary FSR;
- preliminary BCS;
- figures;
- Git commits.

### Deliverable
- Organized PP1 evidence folder.

---

## [ ] Task 3.41 — Prepare the PP1 presentation

### Suggested C3 presentation flow
1. Component title.
2. Problem.
3. Research gap.
4. Objective.
5. AOP-BCS concept.
6. Audit dataset.
7. Fixed redox set.
8. P1/P2/P3 methodology.
9. Implemented architecture.
10. Dataset-preparation progress.
11. Perturbation-engine progress.
12. Predictor-integration status.
13. Pilot experiment.
14. Preliminary DeltaScore/PFR/IR/FSR/BCS results.
15. Validation/reproducibility evidence.
16. Challenges and unresolved dependencies.
17. Work planned after PP1.

### Deliverable
- Final PP1 slide deck and speaking notes.

---

## [ ] Task 3.42 — PP1 rehearsal and final verification

### Subtasks
- Run the pilot pipeline again from a clean configuration.
- Confirm generated files are reproducible.
- Confirm all unit tests pass.
- Confirm presentation figures match the latest result files.
- Confirm no dummy predictor result is presented as scientific evidence.
- Confirm predictor-access limitations are stated accurately.
- Practice explaining:
  - why C3 is an audit rather than a classifier;
  - why W/Y/H/M/C were fixed;
  - why P1, P2 and P3 are needed;
  - why P2 uses BLOSUM62 >= +1;
  - what IR means;
  - what FSR means;
  - why `BCS = IR × (1 - FSR)`;
  - what remains after PP1.

### Deliverable
- PP1-ready Component 3 implementation and presentation.

---

# PP1 Quality Gate

Before considering the PP1 implementation stage complete, verify the following.

## Must be working by PP1
- [x] Team repository cloned and C3 branch created.
- [ ] C3 environment/configuration works.
- [x] Audit sequences acquired.
- [x] Sequences standardized and validated.
- [x] 3–50 AA filter applied.
- [ ] 90% CD-HIT deduplication completed or demonstrably working on the intended dataset.
- [ ] Redox filter `{W,Y,H,M,C}` applied.
- [ ] Residue annotation works.
- [ ] P1 generator works.
- [ ] P2 generator works using BLOSUM62 >= +1.
- [ ] P3 random-control generator works.
- [ ] One-position mutation validation works.
- [ ] Automated tests pass.
- [ ] Common predictor interface exists.
- [ ] Predictor-access status is documented.
- [ ] At least one real predictor has been successfully scored if technically accessible.
- [ ] Pilot original/perturbed scores are stored.
- [ ] DeltaScore is computed.
- [ ] Prediction flips are computed.
- [ ] IR is computed.
- [ ] FSR is computed.
- [ ] Preliminary BCS is computed.
- [ ] Run configuration/seed/version information is recorded.
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

A concise explanation for PP1 is:

> “I have implemented the core AOP-BCS behavioural-audit pipeline. The system prepares a validated AOP subject set, identifies the fixed W/Y/H/M/C redox positions, generates and validates P1, P2 and P3 one-position perturbations, sends original and perturbed sequences through available AOP predictors, records score changes and prediction flips, and calculates preliminary IR, FSR and BCS values. The full five-predictor experiment, statistical hypothesis testing and SHAP-faithfulness analysis continue after PP1.”

