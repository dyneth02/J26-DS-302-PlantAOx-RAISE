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
- [x] Download/locate Multi-AOP unified benchmark and identify the positive records.
- [x] Download/locate AnOxPePred and separate active versus experimentally inactive records.
- [ ] Acquire any annotation references required to justify E1/E2 tier assignments. *(tiering uses AnOxPePred's own FRS/Chelator assay columns directly; no additional external annotation reference was acquired beyond the two source files)*
- [ ] Register source URLs, access dates, releases, citations, and license/access restrictions. *(not done — see 1.2; `fr1_acceptance_report.md` §4/§9)*
- [x] Validate file checksums, parser compatibility, and source record counts. *(SHA-256 computed, parsers tested, counts verified — `fr1_acceptance_report.md` §4)*

## 1.2 — Dataset Registry and Versioning
**Not started.** No `data_registry.csv` exists yet; this entire bucket is an open gap, explicitly
named (not silently skipped) in `fr1_acceptance_report.md` §4/§9 and `IMPLEMENTATION_STATUS.md`'s
decision log (2026-10-14). Recommend scheduling separately — it does not block FR2/FR3 work on
`pp1_baseline_v1`.
- [ ] Update the existing dataset-registry compendium rather than creating duplicate registries.
- [ ] Assign source IDs and immutable raw-file version IDs.
- [ ] Record schemas, row/sequence counts, file sizes, and checksums.
- [ ] Save unchanged raw files under versioned raw-data storage.
- [ ] Document provenance and redistributability in a dataset README.

## 1.3 — Positive Pool Integration and Cleaning
- [x] Extract AOP-positive records from both sources using verified label meanings.
- [x] Normalize amino-acid case, alphabet, sequence whitespace, and invalid residues.
- [x] Apply and document agreed peptide-length inclusion/exclusion rules.
- [x] Generate stable unique peptide IDs and standardized FASTA headers.
- [x] Merge records without discarding their multiple-source evidence links.
- [x] Detect and remove exact cross-source sequence duplicates; log all exclusions.

## 1.4 — Evidence Tier Classification
- [x] Assign **E1** only where an AOP-specific experimental assay is documented.
- [x] Assign **E2** to antioxidant-annotated peptides lacking assay-level documentation.
- [ ] Identify **E3** bioactivity-adjacent records; exclude these from labeled positives and treat as unlabeled when appropriate. *(no E3 source integrated yet — depends on later bioactivity-pool work, e.g. Bucket 2.2)*
- [x] Store assay type, assay evidence, source reference, annotation, and original IDs.
- [x] Establish precedence and review rules for contradictory labels or multiple sources. *(the 179-conflict resolution policy, see `fr1_acceptance_report.md` §6)*
- [x] Summarize E1/E2/E3 counts and provenance, separating unknown/unresolved evidence.
- [ ] Review ambiguous tier assignments and record supervisor-approved adjudications. *(pending — see Supervisor Acceptance Checklist below)*

## 1.5 — CD-HIT Redundancy Reduction
- [x] Install/configure CD-HIT and record the software version. *(4.8.1, user-space micromamba env — no root access was available; see IMPLEMENTATION_STATUS.md)*
- [x] Run the proposed **90% identity** clustering on curated labeled positives.
- [x] Apply reproducible cluster-representative selection rules.
- [x] Preserve evidence/provenance for sequences merged into each cluster.
- [x] Export cluster assignments, representatives, and before/after counts.
- [x] Verify representative integrity and no unintended evidence loss. *(0 sequences dropped, confirmed by test)*

## 1.6 — GraphPart Homology-Controlled Splitting
- [x] Install/configure GraphPart and record software version and parameters. *(graph-part 1.0.2 + EMBOSS 6.6.0.0, same env as CD-HIT)*
- [x] Create **40% identity** homology-controlled folds/splits for positives.
- [x] Export and freeze train/validation/test or CV-fold indices. *(frozen under `pp1_baseline_v1`)*
- [x] Programmatically verify cross-partition homology constraints. *(GraphPart's own convergence report: 0 residual violations)*
- [ ] Check independence from reserved AnOxPePred experimentally inactive controls. *(confirmed disjoint by exact sequence identity; the deeper 40%-homology check against the external control is Bucket 2.6's job and hasn't started)*
- [x] Compare the final pool count against the proposal's approximately 500–800 and SO1 ≥800 targets.
- [x] Export E1/E2, cluster, fold, and length summary tables.

## 1.7 — FR1 Acceptance Testing and Freeze
- [x] Re-run the FR1 pipeline from versioned raw inputs and fixed configuration. *(byte-identical outputs confirmed, `test_fr1_reproducibility.py`)*
- [x] Run automated tests for parsing, evidence assignment, duplicate detection, and split integrity. *(55 tests, `tests/c2_pu/`)*
- [x] Confirm all leakage gates pass or document blocking exceptions.
- [x] Record achieved pool size, tier distribution, and target deviations.
- [x] Freeze curated positive-pool version, configuration, and split index files. *(`pp1_baseline_v1`, checksummed manifest)*
- [x] Publish FR1 completion report and demonstration-ready artifacts. *([`fr1_acceptance_report.md`](fr1_acceptance_report.md))*

**FR1 evidence attachments:** dataset registry, provenance table, curated FASTA/CSV/parquet, evidence-tier counts, CD-HIT clusters, GraphPart indices, validation logs, version manifest, and acceptance report.

---

# Bucket 2 — Challenge Pools Setup (FR2)

**Priority:** Mandatory for PP1  
**Definition of done:** Reproducibly generated and frozen C1, C2, and C3 unlabeled pools, with a known-AOP overlap audit, distribution checks, and leakage validation.

## 2.1 — C1 Random Decoy Construction
- [ ] Confirm SwissProt versus UniRef50 sampling specification with supervisor. *(still pending — see IMPLEMENTATION_STATUS.md Known Issues #1)*
- [ ] Register source release, local reference files, and extraction provenance. *(provenance logs exist — `stage_c1_provenance.txt`, `fr2_c1_provenance.jsonl` — but no formal registry file, same gap as Bucket 1.2's `data_registry.csv`)*
- [x] Implement reproducible **3–50 AA** fragment sampling with a fixed seed. *(ported into tested code, `pools.py`; reproduces the saved file exactly from the saved candidate pool — `test_original_construction_is_reproducible_from_scratch`)*
- [x] Construct and verify the **5,000-record** decoy dataset. *(confirmed 5,000 records / 3,786 unique sequences; record-level interpretation confirmed with the project owner, 2026-10-14)*
- [x] Screen available annotations for known bioactivities; record limitations of annotation coverage. *(secondary blocklist verified to reproduce 8,233 kept / 597 excluded exactly; residual coverage gaps documented in `PU_AOP_RESEARCH_CONTEXT.md` §7)*
- [x] Remove known AOP matches, malformed sequences, and duplicates. *(AOP matches: done — 1 found via conservative screening against 1,205 positives + 179 conflicts, swapped out. Malformed sequences: **done, 2026-10-14** — 260/5,000 non-standard-residue (X/B/Z/U) records swapped 1:1 for standard-alphabet replacements, re-screened against the blocklist + positives + conflicts; canonical artifact is now `stage_c1_decoys_v2.fasta`; see IMPLEMENTATION_STATUS.md Known Issues #9/#10 (resolved) and `test_fr2_c1_alphabet_acceptance.py`. Duplicates: **not removed** — kept intentionally, per the record-vs-unique decision above; unique-sequence count shifted to 3,785 as a result of the swap, documented not hidden.)*
- [x] Save C1 FASTA/CSV plus accession/fragment-coordinate mapping and exclusion log. *(`c1_accession_map.csv`, `c1_leakage_exclusion_log.csv`, `c1_leakage_replacement_log.csv` (v1) plus `c1_accession_map_v2.csv`, `c1_alphabet_exclusion_log.csv`, `c1_alphabet_replacement_log.csv` (v2, alphabet-fixed) — no literal fragment coordinates exist to map, since C1 decoys are whole short UniProt entries, not fragments cut by this pipeline; documented in IMPLEMENTATION_STATUS.md)*

## 2.2 — C2 Bioactive Unlabeled Pool Construction
*(Standard-20-amino-acid-alphabet policy, approved 2026-10-14: applied `is_standard_alphabet()` at
initial curation here, not as a post-hoc patch like C1 needed — see IMPLEMENTATION_STATUS.md Known
Issue #10, resolved for C2.)*
- [x] Acquire Peptipedia records and their bioactivity annotations. *(Peptipedia v2.0 Zenodo dump,
  DOI 10.5281/zenodo.21488992, parsed directly as plain-text SQL — see IMPLEMENTATION_STATUS.md for
  why the web app's filtered download wasn't usable)*
- [x] Select peptides with documented non-antioxidant bioactivities (e.g., antimicrobial, antihypertensive). *(2,000 peptides, each with ≥1 reported non-antioxidant activity tag; experimentally-reported preferred over ML-predicted-only)*
- [x] Exclude explicitly antioxidant-annotated peptides. *(Peptipedia activity id 41, "Anti oxidative," excluded regardless of predicted/experimental status; verified zero antioxidant-tagged records in the output, `test_c2_pool_has_no_antioxidant_tagged_records`)*
- [ ] Cross-reference known AOP resources including AODB and DFBP, with additional available reference sets. *(**not done** — neither AODB nor DFBP is among Peptipedia's 76 integrated source databases; see IMPLEMENTATION_STATUS.md Known Issue #11)*
- [x] Deduplicate and curate approximately **2,000** eligible peptides. *(exactly 2,000 unique sequences, unique peptide IDs, deduplicated by sequence across Peptipedia's internal duplicate IDs)*
- [x] Retain original bioactivity categories and provenance without assigning confirmed-negative status. *(`c2_activity_map.csv` records every activity id/name and predicted-vs-experimental flag per peptide; framed as "unlabeled, assumed non-antioxidant" throughout, never "confirmed negative")*
- [x] Export C2 FASTA/CSV and inclusion/exclusion summary. *(`stage_c2_bioactive_unlabeled.fasta`, `c2_activity_map.csv`, `c2_build_report.json`, `fr2_c2_provenance.jsonl`)*

## 2.3 — C3 ESM-2 Hard-Challenge Construction
*(Standard-20-amino-acid-alphabet policy, approved 2026-10-14: applied `is_standard_alphabet()` at
candidate curation — see IMPLEMENTATION_STATUS.md Known Issue #10, resolved for C3. **Fold-safety
requirement, confirmed with the project owner 2026-10-14: candidate selection uses training-fold-only
positive centroids, never a centroid computed from held-out positives** — see IMPLEMENTATION_STATUS.md
Task 2.3 section for the full leakage rationale and empirical verification.)*
- [x] Prepare an appropriately sized, versioned UniRef50 candidate fragment universe. *(25,000 sequences via UniProt's `/uniref/search` REST API, `identity:0.5 AND length:[3 TO 50]`, sorted `id asc`; versioned raw snapshot at `data/raw/c2_pu/UniRef50/uniref50_candidates.fasta` — not the ~13GB bulk FASTA)*
- [x] Install/test **esm2_t12_35M_UR50D** for consistent sequence embedding. *(done in Bucket 3.2 — reused directly, no changes)*
- [x] Cache positive-pool embeddings and define fold-safe centroid construction. *(834 training positives embedded and cached; 5 separate fold-specific centroids — see IMPLEMENTATION_STATUS.md — not 1 global centroid)*
- [x] Generate candidate embeddings with the same layer and pooling strategy. *(24,732 eligible candidates, same frozen `common/embeddings.py` spec as the positives)*
- [x] Compute and rank candidate-to-positive-centroid distances/similarities. *(cosine similarity, ranked separately per fold against that fold's own training-only centroid — `c3_similarity_ranking.csv`)*
- [ ] Screen known-AOP matches against AODB, DFBP, BIOPEP-UWM, and Multi-AOP. *(**not done** — same gap as C2; Multi-AOP itself IS screened via the FR1 positive pool/conflict log, but AODB/DFBP/BIOPEP-UWM remain unintegrated, see IMPLEMENTATION_STATUS.md Known Issue #11)*
- [x] Select the **top 2,000 eligible** hard-challenge fragments. *(reinterpreted as top-2,000 PER FOLD, not one global top-2,000, to preserve fold-safety — flagged explicitly in IMPLEMENTATION_STATUS.md; union across folds is 2,325 unique sequences)*
- [x] Export C3 FASTA/CSV, similarity ranking, provenance, and screening manifest. *(`stage_c3_esm2_hard_challenges.fasta`, `c3_similarity_ranking.csv`, `c3_build_report.json`, `fr2_c3_provenance.jsonl`)*

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
- [x] Configure PyTorch/fair-esm and GPU/CPU fallback. *(torch 2.14.1+cpu + fair-esm 2.0.0 in the existing `pu_aop` env; CPU-only by confirmed decision despite a real GPU being present — see IMPLEMENTATION_STATUS.md. `resolve_device()` fallback tested both paths: forced-CPU and CUDA-reported-unavailable.)*
- [x] Freeze **esm2_t12_35M_UR50D**, representation layer, tokenization, and pooling method. *(layer 12, 480-dim, BOS/EOS/PAD-excluding mean pool — every element confirmed by inspecting the loaded model/tokenizer directly, not assumed; `common/embeddings.py` module docstring is the canonical spec.)*
- [x] Implement batch inference and input validation. *(`embed_sequences()`: batch_size-chunked inference verified batch-size-invariant; mismatched-length/duplicate-ID/ambiguous-residue inputs all raise explicit errors rather than silently misbehaving.)*
- [ ] Extract embeddings for remaining positives and C1/C2/C3 sequences. *(explicitly out of scope for this task — deliberately deferred, not forgotten. Blocked on deciding the ambiguous-residue policy first, since 260/5,000 C1 decoys will otherwise hard-stop extraction — IMPLEMENTATION_STATUS.md Known Issues #9/#10.)*
- [ ] Verify dimensions, ordering, dtype, and completeness. *(verified for a 5-sequence smoke test; "completeness" at full-dataset scale depends on the extraction task above, not yet done.)*
- [ ] Record model, device, runtime, and extraction parameters. *(the recording mechanism is built and demonstrated — `esm2_smoketest_report.json` — but this checklist item's real target is a full extraction run's parameters, which hasn't happened yet.)*

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
**These are the supervisor's boxes to check, not the pipeline's** — technical acceptance evidence for
every line below is in `fr1_acceptance_report.md` (frozen as `pp1_baseline_v1`, 2026-10-14), but
checking them here would conflate "the pipeline is correct and reproducible" with "a supervisor
reviewed and approved it," which this project's own conflict-resolution and tiering decisions
explicitly should not skip. Left unchecked on purpose; see `fr1_acceptance_report.md` §10 for the
four items that most need a human look.
- [ ] Multi-AOP / AnOxPePred sources and versions documented. *(sources yes — formal registry/version IDs no, see Bucket 1.2)*
- [ ] Original labels, assays, and provenance traceable. *(evidence: §4, 13 passing provenance tests)*
- [ ] E1/E2/E3 operational rules consistently applied and validated. *(E1/E2 yes; E3 not yet populated; the 179-conflict policy needs sign-off, §6/§10)*
- [ ] CD-HIT 90% output reproducible and reviewed. *(reproducibility: evidence attached, §5/§7; "reviewed" = supervisor's part)*
- [ ] GraphPart 40% indices frozen and cross-partition checks pass. *(evidence: §6/§7 — 0 residual violations)*
- [ ] Positive-pool count and data-sufficiency decision documented. *(§2: 1,205 → 925 → 834, vs. SO1 ≥800)*
- [ ] Validated files, summary report, and runnable commands attached. *(§1 commands, §8 frozen files)*

## FR2 — Three-Stage Challenge Pools
**Same convention as FR1's checklist above: these are the supervisor's boxes, left unchecked on
purpose, annotated with where the evidence lives.**
- [ ] C1 has **5,000 verified records**, with source, seed, and screening log. *(5,000 records confirmed, reproducible from seed 42, 0 remaining leakage against FR1 positives/conflicts — see Bucket 2.1 close-out, IMPLEMENTATION_STATUS.md. Still open: 260 non-standard-residue sequences unresolved, Known Issues #9.)*
- [x] C2 has approximately **2,000 curated bioactive unlabeled** records. *(exactly 2,000, built from Peptipedia v2.0; AODB/DFBP cross-reference still outstanding, see Known Issue #11 — not blocking this count)*
- [x] C3 has **2,000 ESM-2-nearest unlabeled** candidates with ranked distances. *(2,000 per fold, fold-safe by construction — 2,325 unique sequences in the exported union; AODB/DFBP/BIOPEP-UWM cross-reference still outstanding, see Known Issue #11 — not blocking this count)*
- [ ] AOP exclusion and pool overlap audits documented. *(done for C1 vs. FR1 positives; C2/C3 not started)*
- [ ] Length, composition, and descriptor checks included. *(C1 length range confirmed 4-50 AA; composition/descriptor checks not yet done for any pool)*
- [ ] External experimentally inactive controls remain separate and verified. *(38-sequence clean external control frozen under FR1's pp1_baseline_v1; its own homology check against positives, per Bucket 2.6, not started)*
- [ ] Pool versions, generated artifacts, and regeneration commands frozen. *(C1 cleanup is reproducible and tested, not yet frozen under a versioned baseline the way FR1 was — recommend doing that once C2/C3 exist, not as three separate partial freezes)*

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
