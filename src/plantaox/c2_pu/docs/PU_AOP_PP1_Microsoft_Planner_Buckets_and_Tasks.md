# PlantAOx-RAISE — Component 02 (PU-AOP)

## Microsoft Planner Work Breakdown: Progress Presentation 01 (PP1)

**Component:** PU-AOP — Evidence-Tiered Positive-Unlabeled Curriculum Classifier with Random-Negative Inflation Audit  
**Purpose:** Supervisor-visible tracking of implementation, verification, and PP1 evidence  
**Planning date:** 13 October 2026  
**PP1 presentation target:** 26 October 2026 *(user-provided; confirm against official schedule)*  
**PP1 checklist submission target:** 30 October 2026 *(user-provided; confirm against official schedule)*  
**Primary completion targets:** FR1 and FR2  
**Stretch target:** FR3, followed by an optional limited FR4 demonstration

> **Status convention:** All boxes begin unchecked. Check a subtask only once its output is verified. Mark an entire Planner task complete only when its documented acceptance evidence is available. This document is a plan, not a claim that work is already completed.

## How to Use This in Microsoft Planner

- **Bucket:** Use each of the six top-level numbered sections below as a Planner bucket.
- **Task:** Create a Planner card for each numbered task (e.g., `2.3 — C3 ESM-2 Hard-Challenge Construction`).
- **Subtasks:** Paste the nested checkbox items into the task's **Checklist**.
- **Description:** Include the task's goal, output artifacts, and relevant FR linkage.
- **Attachments:** Attach GitHub commit/PR links, reports, plots, manifests, or evidence files.
- **Progress:** Use Not started / In progress / Completed, along with an assignee and due date.
- **Recurring quality work:** Keep weekly tracking and logbook work recurring rather than prematurely closing the whole bucket.

## Research Scope and Functional Requirement Map

| Requirement | Proposal definition (abridged) | PP1 priority |
|---|---|---|
| **FR1** | E1/E2/E3 evidence-tiered AOP positives; CD-HIT 90%; GraphPart 40%; verified positive pool and sufficiency check | **Mandatory** |
| **FR2** | Three validated unlabeled pools: C1 random decoys, C2 non-antioxidant-annotated bioactives, C3 ESM-2-nearest hard challenges | **Mandatory** |
| **FR3** | PN, nnPU, Two-Step PU and PU-Bagging on ESM-2 + 15-descriptor features | Stretch; full completion requires all four |
| **FR4** | Sequential nnPU C1 → C2 → C3 with plateau-based transitions (patience 5); E1 1.0 / E2 0.5 | Optional stretch |
| **FR5** | Primary hypotheses, ablations, sensitivity analyses, paired statistical evaluation | Later milestone |
| **FR6** | RNIS = MCC(C1 test) − MCC(C3 test), plus supplementary audits | Later milestone |
| **FR7** | Calibration report and frozen model / PROB_C2 handoff to C3 and C4 | Later milestone |

**Source basis:** *Proposal Report – IT23183018.pdf*: sections 2.2, 3.1–3.6, 5.2–5.3; figures on pp. 28 and 45; PP1 dates supplied by project member. This plan elaborates tasks operationally; it does not assert unverified implementation results.

### Research safeguards and ambiguities to resolve

1. **Target count:** Section 3.2.1 and FR1 describe approximately **500–800** positives after deduplication, while SO1 targets **at least 800**. Report achieved numbers transparently and request supervisor acceptance if the strict SO1 target is unmet.
2. **C1 source:** SO2/FR2 describe SwissProt random decoys; section 3.2.2 names UniRef50. Log a supervisor-approved sampling source and release.
3. **C2 is unlabeled for AOP:** Non-antioxidant bioactivity annotation does **not** prove absence of antioxidant activity. Do not call these confirmed negatives.
4. **C3 is unlabeled:** Known-AOP exclusion reduces documented contamination but cannot prove all C3 sequences are inactive. C3 is a hard negative-*assumption* set for the RNIS audit, not a confirmed-negative training set.
5. **External control:** Experimentally inactive AnOxPePred sequences remain separate and are used for independent, homology-controlled negative-control evaluation.
6. **ESM-2 dependency:** C3 selection needs embeddings before the full feature-fusion pipeline can finish. Begin embedding setup in parallel with Pool Construction.
7. **No leakage:** Candidate selection, centroid fitting, scaling, and evaluation must honor frozen training/evaluation boundaries. Keep independent audit pools isolated from training where applicable.
8. **Dataset labels:** A benchmark positive label alone does not establish E1 assay confirmation. Retain evidence and mark ambiguous cases for review.
9. **Decoy file version:** Verify the actual full **5,000-record FASTA**. An earlier reduced sample contained only 25 records, so do not use the reduced sample as proof of full C1 readiness.

---

# Bucket 1 — Data Preparation (FR1)

**Priority:** Mandatory for PP1  
**Definition of done:** A frozen, provenance-traceable, evidence-tiered positive pool with deduplication, leakage-checked homology partitions, and a documented sufficiency decision.

## 1.1 — Dataset Acquisition
- [ ] Download/locate Multi-AOP unified benchmark and identify the positive records.
- [ ] Download/locate AnOxPePred and separate active versus experimentally inactive records.
- [ ] Acquire any annotation references required to justify E1/E2 tier assignments.
- [ ] Register source URLs, access dates, releases, citations, and license/access restrictions.
- [ ] Validate file checksums, parser compatibility, and source record counts.

## 1.2 — Dataset Registry and Versioning
- [ ] Update the existing dataset-registry compendium rather than creating duplicate registries.
- [ ] Assign source IDs and immutable raw-file version IDs.
- [ ] Record schemas, row/sequence counts, file sizes, and checksums.
- [ ] Save unchanged raw files under versioned raw-data storage.
- [ ] Document provenance and redistributability in a dataset README.

## 1.3 — Positive Pool Integration and Cleaning
- [ ] Extract AOP-positive records from both sources using verified label meanings.
- [ ] Normalize amino-acid case, alphabet, sequence whitespace, and invalid residues.
- [ ] Apply and document agreed peptide-length inclusion/exclusion rules.
- [ ] Generate stable unique peptide IDs and standardized FASTA headers.
- [ ] Merge records without discarding their multiple-source evidence links.
- [ ] Detect and remove exact cross-source sequence duplicates; log all exclusions.

## 1.4 — Evidence Tier Classification
- [ ] Assign **E1** only where an AOP-specific experimental assay is documented.
- [ ] Assign **E2** to antioxidant-annotated peptides lacking assay-level documentation.
- [ ] Identify **E3** bioactivity-adjacent records; exclude these from labeled positives and treat as unlabeled when appropriate.
- [ ] Store assay type, assay evidence, source reference, annotation, and original IDs.
- [ ] Establish precedence and review rules for contradictory labels or multiple sources.
- [ ] Summarize E1/E2/E3 counts and provenance, separating unknown/unresolved evidence.
- [ ] Review ambiguous tier assignments and record supervisor-approved adjudications.

## 1.5 — CD-HIT Redundancy Reduction
- [ ] Install/configure CD-HIT and record the software version.
- [ ] Run the proposed **90% identity** clustering on curated labeled positives.
- [ ] Apply reproducible cluster-representative selection rules.
- [ ] Preserve evidence/provenance for sequences merged into each cluster.
- [ ] Export cluster assignments, representatives, and before/after counts.
- [ ] Verify representative integrity and no unintended evidence loss.

## 1.6 — GraphPart Homology-Controlled Splitting
- [ ] Install/configure GraphPart and record software version and parameters.
- [ ] Create **40% identity** homology-controlled folds/splits for positives.
- [ ] Export and freeze train/validation/test or CV-fold indices.
- [ ] Programmatically verify cross-partition homology constraints.
- [ ] Check independence from reserved AnOxPePred experimentally inactive controls.
- [ ] Compare the final pool count against the proposal's approximately 500–800 and SO1 ≥800 targets.
- [ ] Export E1/E2, cluster, fold, and length summary tables.

## 1.7 — FR1 Acceptance Testing and Freeze
- [ ] Re-run the FR1 pipeline from versioned raw inputs and fixed configuration.
- [ ] Run automated tests for parsing, evidence assignment, duplicate detection, and split integrity.
- [ ] Confirm all leakage gates pass or document blocking exceptions.
- [ ] Record achieved pool size, tier distribution, and target deviations.
- [ ] Freeze curated positive-pool version, configuration, and split index files.
- [ ] Publish FR1 completion report and demonstration-ready artifacts.

**FR1 evidence attachments:** dataset registry, provenance table, curated FASTA/CSV/parquet, evidence-tier counts, CD-HIT clusters, GraphPart indices, validation logs, version manifest, and acceptance report.

---

# Bucket 2 — Challenge Pools Setup (FR2)

**Priority:** Mandatory for PP1  
**Definition of done:** Reproducibly generated and frozen C1, C2, and C3 unlabeled pools, with a known-AOP overlap audit, distribution checks, and leakage validation.

## 2.1 — C1 Random Decoy Construction
- [ ] Confirm SwissProt versus UniRef50 sampling specification with supervisor.
- [ ] Register source release, local reference files, and extraction provenance.
- [ ] Implement reproducible **3–50 AA** fragment sampling with a fixed seed.
- [ ] Construct and verify the **5,000-record** decoy dataset.
- [ ] Screen available annotations for known bioactivities; record limitations of annotation coverage.
- [ ] Remove known AOP matches, malformed sequences, and duplicates.
- [ ] Save C1 FASTA/CSV plus accession/fragment-coordinate mapping and exclusion log.

## 2.2 — C2 Bioactive Unlabeled Pool Construction
- [ ] Acquire Peptipedia records and their bioactivity annotations.
- [ ] Select peptides with documented non-antioxidant bioactivities (e.g., antimicrobial, antihypertensive).
- [ ] Exclude explicitly antioxidant-annotated peptides.
- [ ] Cross-reference known AOP resources including AODB and DFBP, with additional available reference sets.
- [ ] Deduplicate and curate approximately **2,000** eligible peptides.
- [ ] Retain original bioactivity categories and provenance without assigning confirmed-negative status.
- [ ] Export C2 FASTA/CSV and inclusion/exclusion summary.

## 2.3 — C3 ESM-2 Hard-Challenge Construction
- [ ] Prepare an appropriately sized, versioned UniRef50 candidate fragment universe.
- [ ] Install/test **esm2_t12_35M_UR50D** for consistent sequence embedding.
- [ ] Cache positive-pool embeddings and define fold-safe centroid construction.
- [ ] Generate candidate embeddings with the same layer and pooling strategy.
- [ ] Compute and rank candidate-to-positive-centroid distances/similarities.
- [ ] Screen known-AOP matches against AODB, DFBP, BIOPEP-UWM, and Multi-AOP.
- [ ] Select the **top 2,000 eligible** hard-challenge fragments.
- [ ] Export C3 FASTA/CSV, similarity ranking, provenance, and screening manifest.

## 2.4 — Pool Contamination and Leakage Audit
- [ ] Remove within-pool duplicates for C1/C2/C3.
- [ ] Find and resolve overlap among challenge pools and curated positives.
- [ ] Document conflicts with known antioxidant annotations and exclusion outcomes.
- [ ] Verify required homology boundaries for held-out evaluation and training partitions.
- [ ] Record contamination and exclusion counts by database and stage.
- [ ] State explicitly that unknown antioxidant activity can remain undetected.
- [ ] Save automated integrity report and rerunnable checks.

## 2.5 — Biological Distribution and Shortcut-Bias Checks
- [ ] Plot positive-versus-C1/C2/C3 peptide-length distributions.
- [ ] Implement agreed length-stratified sampling or report residual mismatches.
- [ ] Compare amino-acid composition by pool.
- [ ] Compare selected physicochemical descriptor distributions by pool.
- [ ] Optionally produce exploratory UMAP/t-SNE views; do not claim they prove separation.
- [ ] Record potential family/organism/source shortcuts and residual biases.

## 2.6 — External Inactive-Control Preparation
- [ ] Extract genuinely experimentally tested inactive AnOxPePred peptides.
- [ ] Keep them separate from C1/C2/C3 and training unlabeled labels.
- [ ] Run homology checks against the training-positive pool at the proposed 40% boundary.
- [ ] Exclude violating entries and document reasons.
- [ ] Freeze external negative-control records and their provenance.

## 2.7 — FR2 Acceptance Testing and Freeze
- [ ] Regenerate all three pools from frozen scripts/configs.
- [ ] Verify intended counts, sequence validity, source identity, and reproducible sampling.
- [ ] Confirm exclusion, overlap, and leakage reports are complete.
- [ ] Freeze dataset versions and pool manifests.
- [ ] Publish FR2 construction and biological-sanity validation report.

**FR2 evidence attachments:** frozen C1/C2/C3 FASTA/CSV, seed/config, source manifests, C3 similarity ranking, overlap/exclusion report, length/composition/descriptors plots, AnOxPePred inactive-control set, validation report.

---

# Bucket 3 — Feature Engineering Pipeline (FR3 Prerequisite)

**Priority:** High / stretch support  
**Definition of done:** Verified cached features aligned to peptide identifiers, with leakage-safe preprocessing and reproducible loading.

## 3.1 — Physicochemical Descriptor Extraction
- [ ] Define the exact **15 descriptors** and their formulas/units.
- [ ] Implement extraction for every relevant peptide.
- [ ] Check ranges, missing/NaN values, and nonfinite values.
- [ ] Test representative short/long/charged/hydrophobic sequences.
- [ ] Save descriptor matrices with peptide-ID mappings.

## 3.2 — ESM-2 Embedding Pipeline
- [ ] Configure PyTorch/fair-esm and GPU/CPU fallback.
- [ ] Freeze **esm2_t12_35M_UR50D**, representation layer, tokenization, and pooling method.
- [ ] Implement batch inference and input validation.
- [ ] Extract embeddings for remaining positives and C1/C2/C3 sequences.
- [ ] Verify dimensions, ordering, dtype, and completeness.
- [ ] Record model, device, runtime, and extraction parameters.

## 3.3 — Feature Fusion and Preprocessing
- [ ] Align ESM-2 and physicochemical features by stable peptide ID.
- [ ] Concatenate embeddings and 15-descriptor vectors.
- [ ] Fit normalization/scaling using **training fold only**.
- [ ] Apply fitted transforms to validation/test data without refitting.
- [ ] Validate fused model-input shape and ordering.

## 3.4 — Feature Cache and Reproducibility
- [ ] Save cached `.npy` matrices and metadata/index mappings.
- [ ] Version feature extraction configuration and cache schema.
- [ ] Implement cache load/validation utilities.
- [ ] Check shape, dtype, order, missing entries, and checksums.
- [ ] Run an automated feature pipeline smoke test.

## 3.5 — Feature Pipeline Demonstration
- [ ] Demonstrate FASTA/CSV to descriptor/embedding features.
- [ ] Demonstrate cached feature loading without re-embedding.
- [ ] Save representative shape summaries and validation logs.
- [ ] Document one-command reproduction of the demonstration.

**Feature evidence attachments:** descriptor definitions, feature matrices and mappings, embedding manifests, preprocessing config, sanity plots, tests, demo instructions.

---

# Bucket 4 — Model Baselines and PP1 Demonstration (FR3 / Optional FR4)

**Priority:** Stretch, after FR1/FR2 gates  
**Definition of done:** At least a working PN baseline with validated training and metrics; additional nnPU/PU baselines only claimed complete when functional. The full FR3 requires **PN + nnPU + Two-Step PU + PU-Bagging**.

## 4.1 — Shared Experiment Infrastructure
- [ ] Create reusable experiment configuration and run metadata schema.
- [ ] Implement architecture-matched MLP model and consistent feature interface.
- [ ] Implement fold-aware positive/unlabeled data loaders.
- [ ] Fix random seeds and log package/model versions.
- [ ] Add model checkpointing, logs, and run manifests.

## 4.2 — PN Baseline Implementation
- [ ] Implement PN classifier using E1 positives and **C1 assumed negatives**.
- [ ] Connect shared fused representation and frozen partitions.
- [ ] Run monitored training and validation.
- [ ] Confirm probability inference and checkpoint loadability.
- [ ] Save initial results and learning curves.

## 4.3 — Plain nnPU Baseline Implementation
- [ ] Implement non-negative PU risk estimator and unit tests.
- [ ] Prepare labeled E1/E2 positives and unlabeled samples correctly.
- [ ] Choose/document initial positive-class prior π and its limitations.
- [ ] Train C1-only nnPU with no curriculum.
- [ ] Validate loss stability and inference output.
- [ ] Save trained model, logs, and configuration.

## 4.4 — Additional PU Baselines
- [ ] Install/test PULearn-compatible dependencies.
- [ ] Implement Two-Step PU.
- [ ] Implement PU-Bagging.
- [ ] Use comparable partitions/features and document algorithm differences.
- [ ] Save baseline artifacts and configs.

## 4.5 — Initial Model Evaluation and Testing
- [ ] Run reduced-data one-fold PN smoke test.
- [ ] Run reduced-data one-fold nnPU smoke test.
- [ ] Test additional PU baselines where implemented.
- [ ] Verify MCC and AUPRC calculations on labeled/assumption-based sets as appropriate.
- [ ] Check probability bounds, NaN/Inf, stability, and checkpoints.
- [ ] Generate a clearly labeled preliminary comparison table.

## 4.6 — Optional FR4 Curriculum Prototype
- [ ] Implement nnPU progression **C1 → C2 → C3**.
- [ ] Transition on validation-loss plateau (**patience = 5**).
- [ ] Apply E1 = 1.0 / E2 = 0.5; E3 excluded from labeled positives.
- [ ] Log fold-specific transition epochs and stage-wise loss.
- [ ] Demonstrate one reduced-data end-to-end curriculum run.

## 4.7 — PP1 Technical Report
- [ ] Document FR1 datasets, evidence tiers, splits, and validation.
- [ ] Document FR2 three-stage pools, integrity checks, and bias checks.
- [ ] Describe feature pipeline and cache reproducibility.
- [ ] Include only verified baseline results and limitations.
- [ ] Disclose unresolved constraints and differences from proposal.
- [ ] Add FR-to-artifact traceability table.
- [ ] Complete internal technical review and proofread.

## 4.8 — PP1 Presentation and Live Demo
- [ ] Prepare slides on C2 motivation, methodology, and architecture.
- [ ] Show quantitative FR1 acceptance evidence.
- [ ] Show three FR2 pools and contamination/distribution reports.
- [ ] Prepare dataset/pipeline demonstration and cached artifacts.
- [ ] Demonstrate feature loading / baseline predictions if functional.
- [ ] Rehearse; prepare offline screenshots/video as fallback.
- [ ] Incorporate supervisor feedback.

**Model/demo evidence attachments:** configurations, checkpoints, training logs, test outputs, initial results table, presentation slides, demo video/screenshots, report and traceability matrix.

---

# Bucket 5 — Ongoing Progress and Quality Control

**Priority:** Continuous across all buckets  
**Definition of done:** Current, reviewable status, complete decision log, reproducible artifacts, and regularly refreshed validation evidence.

## 5.1 — Weekly Progress and Scope Tracking
- [ ] Update Planner card progress/checklists weekly.
- [ ] Compare actual work to Gantt milestones.
- [ ] Update blockers, risks, dependencies, and mitigation owners.
- [ ] Review the critical path and next deliverables.
- [ ] Record agreed scope changes and action items.

## 5.2 — Supervisor Consultation Management
- [ ] Attend/schedule regular supervisor consultations.
- [ ] Record participants, decisions, feedback, and dates.
- [ ] Convert agreed feedback into trackable tasks.
- [ ] Attach supporting evidence and close resolved items.

## 5.3 — Continuous Data and Pipeline Testing
- [ ] Maintain parsing/cleaning/tier-assignment tests.
- [ ] Maintain deduplication, GraphPart, and leakage tests.
- [ ] Maintain challenge-pool contamination and reproducibility tests.
- [ ] Maintain feature cache validation tests.
- [ ] Maintain baseline/metrics sanity tests when applicable.

## 5.4 — Version Control and Artifact Management
- [ ] Commit code/config changes with meaningful messages.
- [ ] Version datasets, split indices, cache manifests, and experiments.
- [ ] Keep environment and setup instructions current.
- [ ] Back up research-critical outputs and model checkpoints.
- [ ] Link commits and evidence files to Planner tasks.

## 5.5 — Research Logbook and Decision Log
- [ ] Record dated activities, experiments, results, and obstacles.
- [ ] Document methodological decisions and deviations.
- [ ] Record bug fixes and failed attempts where relevant.
- [ ] Include supervisor sign-offs when required.
- [ ] Keep logbook evidence aligned with Planner statuses.

**Quality evidence attachments:** updated board, meeting minutes, Git history, test reports, experiment manifests, decision log, and signed logbook entries.

---

# Bucket 6 — PP1 Milestone and Submission

**Priority:** Milestone-critical  
**Definition of done:** Demonstrated requirements, presentation delivery, collected feedback, and verified submission artifacts.

## 6.1 — PP1 Readiness Gate
- [ ] Verify every FR1 acceptance condition and evidence link.
- [ ] Verify every FR2 acceptance condition and evidence link.
- [ ] Report actual FR3/FR4 completion without overstating status.
- [ ] Test live and offline fallback demo routes.
- [ ] Complete final technical evidence checklist.

## 6.2 — Progress Presentation 01 (Target: 26 October 2026)
- [ ] Finalize slides and rehearsal/demo sequence.
- [ ] Deliver component presentation to evaluation panel.
- [ ] Demonstrate verified completed FR functionality.
- [ ] Capture panel questions and feedback.
- [ ] Create actions for corrections or follow-up work.

## 6.3 — PP1 Checklist Submission (Target: 30 October 2026)
- [ ] Compile official checklist and required supporting evidence.
- [ ] Validate links to report, code, datasets, and test records.
- [ ] Obtain necessary review/sign-off.
- [ ] Submit required material by confirmed deadline.
- [ ] Save proof of submission.

## 6.4 — Post-PP1 Transition
- [ ] Prioritize panel feedback and unresolved PP1 issues.
- [ ] Replan unfinished tasks without silently marking them complete.
- [ ] Confirm FR3–FR7 scope and sequence for PP2.
- [ ] Update Gantt chart, milestones, and risk register.

---

# Suggested PP1 Execution Schedule

*Operational planning suggestion, not a schedule explicitly stated in the proposal. Adjust to actual progress, team capacity, and official dates.*

| Window | Priority |
|---|---|
| **12–15 Oct** | Raw-data inventory, integration, tier rules, C1/C2 data acquisition and checks |
| **14–19 Oct** | CD-HIT, GraphPart, ESM-2 setup, C3 retrieval; begin validation in parallel |
| **18–22 Oct** | Complete FR1/FR2 quality gates and freeze; attempt feature cache / PN baseline |
| **22–24 Oct** | nnPU if feasible; report, figures, slides, and offline demo |
| **25 Oct** | Final acceptance validation and rehearsal |
| **26 Oct** | PP1 presentation |
| **30 Oct** | Checklist submission |

**Suggested decision gate (~19 October):** If required source data or integrity tests remain blocking, prioritize two **verified** FRs over a larger set of unvalidated features.

# Supervisor Acceptance Checklist

## FR1 — Evidence-Tiered Positive Pool
- [ ] Multi-AOP / AnOxPePred sources and versions documented.
- [ ] Original labels, assays, and provenance traceable.
- [ ] E1/E2/E3 operational rules consistently applied and validated.
- [ ] CD-HIT 90% output reproducible and reviewed.
- [ ] GraphPart 40% indices frozen and cross-partition checks pass.
- [ ] Positive-pool count and data-sufficiency decision documented.
- [ ] Validated files, summary report, and runnable commands attached.

## FR2 — Three-Stage Challenge Pools
- [ ] C1 has **5,000 verified records**, with source, seed, and screening log.
- [ ] C2 has approximately **2,000 curated bioactive unlabeled** records.
- [ ] C3 has **2,000 ESM-2-nearest unlabeled** candidates with ranked distances.
- [ ] AOP exclusion and pool overlap audits documented.
- [ ] Length, composition, and descriptor checks included.
- [ ] External experimentally inactive controls remain separate and verified.
- [ ] Pool versions, generated artifacts, and regeneration commands frozen.

## FR3 / FR4 — Stretch Claims
- [ ] Only claim partial FR3 when fewer than PN, nnPU, Two-Step PU, and PU-Bagging work.
- [ ] Do not claim FR4 complete from a single demonstration unless full acceptance requirements are met.
- [ ] Clearly label one-fold/reduced-data experiments as smoke tests, not final statistical evidence.

# Research Deliverable Registry (Recommended)

| Artifact | Suggested filename | Purpose |
|---|---|---|
| Source registry | `data_registry.csv` | Versions, licensing, identifiers and checksums |
| Curated positives | `aop_positives.parquet` | Unified evidence-tiered positive table |
| Provenance map | `aop_provenance.csv` | Links curated IDs to original records/evidence |
| CD-HIT report | `cdhit_clusters.tsv` | 90% identity cluster relationships |
| Split indices | `graphpart_splits.csv` | Frozen homology-aware partitions |
| C1 pool | `stage_c1_decoys.fasta` | Verified 5,000 random decoys |
| C2 pool | `stage_c2_bioactive_unlabeled.fasta` | Bioactive, AOP-unlabeled challenges |
| C3 pool | `stage_c3_hard_unlabeled.fasta` | ESM-2-nearest hard challenges |
| Pool manifest | `challenge_pool_manifest.json` | Counts, configs, seeds, exclusions |
| Pool report | `challenge_pool_quality_report.md` | Bias/integrity and screening evidence |
| Inactive control | `anoxpepred_inactives_holdout.csv` | External experimentally inactive control |
| Descriptor cache | `descriptors.npy` + ID map | 15 physicochemical descriptors |
| Embedding cache | `esm2_embeddings.npy` + ID map | Consistent cached ESM-2 features |
| FR1 verification | `fr1_acceptance_report.md` | Supervisor-auditable proof of FR1 |
| FR2 verification | `fr2_acceptance_report.md` | Supervisor-auditable proof of FR2 |
| PP1 summary | `pp1_component02_progress.md` | Actual status, results, limitations |

*These are suggested names, not mandatory paths from the proposal. Adapt them to the established shared repository contracts; do not create duplicate data artifacts.*

---

## Reference Locations Within the Proposal

- **Pages 20–21:** SO1–SO6 and quantitative target traceability.
- **Pages 23–27:** Experiment tiers, positive/unlabeled sources, validation, feature representation, development phases.
- **Pages 28–29:** Component and overall PlantAOx-RAISE system architecture figures.
- **Pages 31–32:** FR1–FR7 and non-functional requirements.
- **Page 45:** Component 02 Work Breakdown Structure.
- **Page 47:** Project Gantt chart.
- **Pages 56–58:** Planner and research logbook examples in appendices.

**Version:** 1.0 — PP1 execution-focused Planner breakdown.
