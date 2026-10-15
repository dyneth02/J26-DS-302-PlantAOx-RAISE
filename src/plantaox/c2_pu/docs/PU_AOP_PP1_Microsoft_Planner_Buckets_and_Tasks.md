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
*(Status 2026-10-14: RESOLVED and technically accepted. Both findings fixed per project-owner-approved
Decisions A/B; audit rerun against the corrected canonical pools. `fr2_pool_audit_report.json` records
`ready_for_technical_acceptance: true`, re-derived from the live artifacts, not hand-edited. Canonical
C1/C2 are now `stage_c1_decoys_v3.fasta` / `stage_c2_bioactive_unlabeled_v2.fasta`.)*
- [x] Remove within-pool duplicates for C1/C2/C3. *(C1 intentionally retains natural record-level duplicates by design, confirmed decision — see IMPLEMENTATION_STATUS.md; C2 and C3 have zero duplicate sequences, confirmed by `sequence_integrity_report`)*
- [x] Find and resolve overlap among challenge pools and curated positives. *(found AND resolved — the 8 C1/C2 exact-sequence duplicates (11 actual records) were removed from C1 and replaced, screened against FR1 positives/179 conflicts/C2/C3; re-verified zero overlap in `stage_c1_decoys_v3.fasta`)*
- [x] Document conflicts with known antioxidant annotations and exclusion outcomes. *(`audit_external_aop_screen.json`: BIOPEP-UWM screened, zero hits in C1 v3/C2 v2/C3; 700/1,205 positives and 22/179 conflicts independently corroborated; AODB/DFBP documented as inaccessible, not silently skipped; the 2 BIOPEP-UWM-vs-AnOxPePred-inactive-control conflicts preserved as documented uncertainties)*
- [x] Verify required homology boundaries for held-out evaluation and training partitions. *(the C2 peptide homologous to an E1 FR1 positive was excluded and replaced, confirmed via EMBOSS needle alignment (77.8% full-length identity) before deciding; the 11 remaining C1↔C2-only near-duplicate candidates (3 of the original 14 resolved as a side effect) were reviewed individually — recommended as an accepted, documented limitation since none involve FR1 positives or a plausible antioxidant mechanism; see `audit_cross_pool_homology_clusters.csv`)*
- [x] Record contamination and exclusion counts by database and stage. *(`audit_integrity_report.json`, `audit_exact_overlap_matrix.csv`/`_detail.csv`, `audit_external_aop_screen.json`, `audit_cross_pool_homology_summary.json`/`_clusters.csv`, plus `c1_cross_pool_fix_report.json`/`c2_cross_pool_fix_report.json` for the two resolutions)*
- [x] State explicitly that unknown antioxidant activity can remain undetected. *(AODB/DFBP unscreened — documented as access failures, not coverage claims; BIOPEP-UWM/Multi-AOP/AnOxPePred screening narrows but never eliminates this risk, stated plainly in IMPLEMENTATION_STATUS.md)*
- [x] Save automated integrity report and rerunnable checks. *(`python -m plantaox.c2_pu.run fr2-pool-audit`, `fr2-c1-cross-pool-fix`, `fr2-c2-cross-pool-fix`; 55 tests across audit/biopep/C3-contract/pools-fix/acceptance files, all passing, including byte-identical reproducibility for both fixes)*

## 2.5 — Biological Distribution and Shortcut-Bias Checks
*(Status 2026-10-14: COMPLETE, against the canonical C1 v3/C2 v2/C3 union. Uses a small, independently-
computed descriptor set — NOT Bucket 3.1's 15-descriptor pipeline, which remains unstarted; see
IMPLEMENTATION_STATUS.md.)*
- [x] Plot positive-versus-C1/C2/C3 peptide-length distributions. *(quantified via two-sample KS-test rather than visual-only comparison, length KS=0.63-0.86 across pools, all p≈0; one summary chart rendered for the user; full per-sequence table in `distribution_descriptor_table.csv`)*
- [x] Implement agreed length-stratified sampling or report residual mismatches. *(residual mismatches reported, not resampled — a resample would be a further dataset-version change outside this read-only task's scope and wasn't requested)*
- [x] Compare amino-acid composition by pool. *(`distribution_aa_composition.csv` — FR1 positives are Pro-enriched (10.6% vs 4-6% in C1/C2/C3), C2 is Cys-enriched (5.5% vs 1.4-2.6% elsewhere), both biologically explainable, not noise)*
- [x] Compare selected physicochemical descriptor distributions by pool. *(molecular weight, net charge pH7, GRAVY, aromaticity — `distribution_ks_comparison.csv`; every pool differs significantly from positives on every descriptor)*
- [x] Optionally produce exploratory UMAP/t-SNE views; do not claim they prove separation. *(deliberately deferred — the KS-test results already answer the underlying question more precisely than a 2D projection would; not silently skipped)*
- [x] Record potential family/organism/source shortcuts and residual biases. *(`distribution_shortcut_report.json`: C1 spans 1,708 organisms, no single organism >2.1% share; C2 spans 123 activity tags, "Therapeutic" largest at 14.4%; FR1 positives have NO organism metadata available — documented as an unchecked gap, not assumed clean)*

## 2.6 — External Inactive-Control Preparation
*(Status 2026-10-14: COMPLETE and technically accepted. 38 records validated against the frozen
`pp1_baseline_v1` copy; canonical validated artifact is `anoxpepred_external_control_validated.csv`.)*
- [x] Extract genuinely experimentally tested inactive AnOxPePred peptides. *(already extracted in Bucket 1 as `anoxpepred_inactives_clean.csv`, frozen in `pp1_baseline_v1`; 38 records re-verified here, not re-extracted)*
- [x] Keep them separate from C1/C2/C3 and training unlabeled labels. *(confirmed zero exact-sequence overlap with C1 v3/C2 v2/C3/positives/179 conflicts; the labeling rule — "inactive under AnOxPePred's assay, not universally proven non-antioxidant" — stated explicitly in every output)*
- [x] Run homology checks against the training-positive pool at the proposed 40% boundary. *(EMBOSS `needleall`, all 38×1,205=45,790 pairs, not CD-HIT shortcut; zero pairs reach both ≥40% identity and a biologically-interpretable ≥15 AA alignment length — the 394 pairs above 40% are all ≤12 AA short-fragment chance matches, reported not hidden; held-out-fold independence confirmed structurally)*
- [x] Exclude violating entries and document reasons. *(zero violations found — nothing to exclude; the 2 BIOPEP-UWM-vs-AnOxPePred conflicts are flagged, with a recommendation to retain presented for project-owner approval, not unilaterally excluded)*
- [x] Freeze external negative-control records and their provenance. *("Freeze" realized as `anoxpepred_external_control_validated.csv` + `ext_control_validation_report.json` + `fr2_ext_control_provenance.jsonl`; full immutable-package freeze happens at Task 2.7/FR2 freeze, which bundles this output)*

## 2.7 — FR2 Acceptance Testing and Freeze
*(Status 2026-10-14: COMPLETE. Technically accepted and frozen as `pp2_baseline_v1`. See
`fr2_acceptance_report.md` for the full account; scientific sign-off explicitly not claimed.)*
- [x] Regenerate all three pools from frozen scripts/configs. *(not literally re-run from scratch this pass — reproducibility already re-verified per-stage via dedicated tests; see below)*
- [x] Verify intended counts, sequence validity, source identity, and reproducible sampling. *(C1 5,000/3,788 unique, C2 2,000, C3 2,325-sequence union + 5×2,000 fold rankings, external control 38 — all re-confirmed directly from the frozen files; full test suite including every reproducibility check run complete, 177 passed/1 skipped, 16m34s)*
- [x] Confirm exclusion, overlap, and leakage reports are complete. *(`fr2-pool-audit` rerun fresh immediately before freezing: `ready_for_technical_acceptance: true`)*
- [x] Freeze dataset versions and pool manifests. *(`pp2_baseline_v1`, 28 files, checksummed `MANIFEST.json`; `pp1_baseline_v1` confirmed untouched before and after)*
- [x] Publish FR2 construction and biological-sanity validation report. *(`fr2_acceptance_report.md`, mirrors `fr1_acceptance_report.md`'s structure)*

**FR2 evidence attachments:** frozen C1/C2/C3 FASTA/CSV, seed/config, source manifests, C3 similarity ranking, overlap/exclusion report, length/composition/descriptors plots, AnOxPePred inactive-control set, validation report.

---

# Bucket 3 — Feature Engineering Pipeline (FR3 Prerequisite)

**Priority:** High / stretch support  
**Definition of done:** Verified cached features aligned to peptide identifiers, with leakage-safe preprocessing and reproducible loading.

## 3.1 — Physicochemical Descriptor Extraction
- [x] Define the exact **15 descriptors** and their formulas/units. (schema `descriptors_v1`,
  `common/descriptors.py`; approved by project owner 2026-10-14, see IMPLEMENTATION_STATUS.md)
- [x] Implement extraction for every relevant peptide. (FR1 positives, C1, C2, C3 union, external
  control — via `curation/descriptor_extraction.py` + `run.py::run_fr3_descriptors()`, CLI `fr3-descriptors`)
- [x] Check ranges, missing/NaN values, and nonfinite values. (`fr3_validation_report.json`: zero
  missing/nonfinite across all 9,356 real rows; one diagnostic-only high-correlation pair flagged)
- [x] Test representative short/long/charged/hydrophobic sequences. (29 unit tests in
  `test_descriptors.py`, including aromatic/cysteine-rich/proline-rich cases)
- [x] Save descriptor matrices with peptide-ID mappings. (`fr3_descriptor_table.parquet` +
  `fr3_record_map.csv`)

## 3.2 — ESM-2 Embedding Pipeline
- [x] Configure PyTorch/fair-esm and GPU/CPU fallback. *(torch 2.14.1+cpu + fair-esm 2.0.0 in the existing `pu_aop` env; CPU-only by confirmed decision despite a real GPU being present — see IMPLEMENTATION_STATUS.md. `resolve_device()` fallback tested both paths: forced-CPU and CUDA-reported-unavailable.)*
- [x] Freeze **esm2_t12_35M_UR50D**, representation layer, tokenization, and pooling method. *(layer 12, 480-dim, BOS/EOS/PAD-excluding mean pool — every element confirmed by inspecting the loaded model/tokenizer directly, not assumed; `common/embeddings.py` module docstring is the canonical spec.)*
- [x] Implement batch inference and input validation. *(`embed_sequences()`: batch_size-chunked inference verified batch-size-invariant; mismatched-length/duplicate-ID/ambiguous-residue inputs all raise explicit errors rather than silently misbehaving.)*
- [x] Extract embeddings for remaining positives and C1/C2/C3 sequences. *(all 9,356 unique sequences from `fr3_descriptor_table.parquet`: 1,205 FR1 positives + 3,788 C1 + 2,000 C2 + 2,325 C3-union + 38 external control. 3,159 reused directly from Bucket 2.3's existing caches, 6,197 freshly embedded. CLI stage `fr3-embeddings`, see IMPLEMENTATION_STATUS.md.)*
- [x] Verify dimensions, ordering, dtype, and completeness. *(`fr3_embeddings_validation_report.json`: shape (9356, 480), dtype float32, all finite, peptide_id order confirmed identical to `fr3_descriptor_table.parquet`'s row order.)*
- [x] Record model, device, runtime, and extraction parameters. *(`fr3_embeddings_manifest.json`: model name/layer/dim, reused-vs-fresh counts, per-pool coverage, peptide-ID-order and cache SHA-256, elapsed seconds.)*

## 3.3 — Feature Fusion and Preprocessing
- [x] Align ESM-2 and physicochemical features by stable peptide ID. *(`load_and_validate_fusion_inputs()`: hard-fails on any peptide_id/order/pool mismatch between `fr3_descriptor_table.parquet` and `fr3_embeddings.npz`, rather than silently reindexing.)*
- [x] Concatenate embeddings and 15-descriptor vectors. *(`build_raw_fused_matrix()`: [esm2_0..esm2_479, then descriptors_v1's 15 names], schema `fusion_v1`, 9,356×495 float32.)*
- [x] Fit normalization/scaling using **training fold only**. *(one z-score scaler per GraphPart fold, fit exclusively on that fold's training-positive rows — mirrors the C3 fold-safe-centroid precedent; see IMPLEMENTATION_STATUS.md for the full rationale.)*
- [x] Apply fitted transforms to validation/test data without refitting. *(`apply_scaler()` is transform-only; verified applying each fold's scaler to its own held-out positives + every unlabeled pool produces finite output with no refit call anywhere in the path.)*
- [x] Validate fused model-input shape and ordering. *(`fr3_fusion_validation_report.json`: shape (9356, 495), all finite, peptide-ID order confirmed identical to Task 3.1/3.2's own order via matching SHA-256.)*

## 3.4 — Feature Cache and Reproducibility
- [x] Save cached `.npy` matrices and metadata/index mappings. *(5 fold-specific `.npz` caches — peptide_ids/pools/features/feature_names/scaler_mean/scaler_std — gitignored per repo policy; committed manifest records path/hash/shape/dtype per fold.)*
- [x] Version feature extraction configuration and cache schema. *(`feature_cache_v1`, recorded in `fr3_feature_cache_manifest.json` alongside the upstream `fusion_v1` schema version it was built from.)*
- [x] Implement cache load/validation utilities. *(`common/feature_cache.py`: `load_fold_feature_cache`, `get_pool_rows`, `get_training_rows`, `get_held_out_rows`, `get_c3_fold_challenge_rows` — torch/WSL-free.)*
- [x] Check shape, dtype, order, missing entries, and checksums. *(strict SHA-256 + shape/dtype/schema-version/scaler-identity verification before any array is trusted; 6 corruption modes tested.)*
- [x] Run an automated feature pipeline smoke test. *(subprocess-isolated: loads a real cache, confirms `torch`/`esm` never enter `sys.modules`, completes in <10s.)*

## 3.5 — Feature Pipeline Demonstration
- [x] Demonstrate FASTA/CSV to descriptor/embedding features. *(7 real peptide_ids, standard-alphabet/3-50AA validation + live `compute_descriptors_batch()`, cross-checked against the frozen descriptor table; embeddings loaded from cache per the brief's "heavy extraction may be precomputed" allowance.)*
- [x] Demonstrate cached feature loading without re-embedding. *(`load_fold_feature_cache()` on the real fold-0 495-dim cache; zero ESM-2/WSL calls, verified via a subprocess-isolated smoke test.)*
- [x] Save representative shape summaries and validation logs. *(`fr3_demo_output.json`, committed — schema versions, shapes at every stage, pool coverage, per-peptide scaled-feature preview, explicit pass/fail validation block.)*
- [x] Document one-command reproduction of the demonstration. *(`FR3_FEATURE_PIPELINE_DEMO.md`: `python -m plantaox.c2_pu.run fr3-demo`, prerequisites, and the expected-output reference.)*

**Bucket 3 (Feature Engineering Pipeline) is now fully closed out as of Task 3.5's acceptance.** FR3
itself remains incomplete pending the four classification baselines and their evaluation (Bucket 4).

**Feature evidence attachments:** descriptor definitions, feature matrices and mappings, embedding manifests, preprocessing config, sanity plots, tests, demo instructions.

---

# Bucket 4 — Model Baselines and PP1 Demonstration (FR3 / Optional FR4)

**Priority:** Stretch, after FR1/FR2 gates  
**Definition of done:** At least a working PN baseline with validated training and metrics; additional nnPU/PU baselines only claimed complete when functional. The full FR3 requires **PN + nnPU + Two-Step PU + PU-Bagging**.

## 4.1 — Shared Experiment Infrastructure
- [x] Create reusable experiment configuration and run metadata schema. *(`experiment_config.py::ExperimentConfig`, validated dataclass; resolved config + source-artifact checksums + git revision + seed context recorded per run by `run_recorder.py`.)*
- [x] Implement architecture-matched MLP model and consistent feature interface. *(`models.py::BinaryMlp`/`MlpArchitecture` — 495→128→64→1, configurable; architecture + training algorithm deliberately NOT coupled, per Task 4.1 scope.)*
- [x] Implement fold-aware positive/unlabeled data loaders. *(`experiment_data.py::build_experiment_data`, built on the accepted `common/feature_cache.py` loader — train/validation/held-out positives, C1, C2, fold-specific C3, external control, with cross-subset identity/sequence-leakage checks.)*
- [x] Fix random seeds and log package/model versions. *(`common/seeding.py::set_global_seed` — Python/NumPy/PyTorch, CPU-verified bit-identical reproducibility; records CUDA availability/device, deterministic-algorithm setting, library versions.)*
- [x] Add model checkpointing, logs, and run manifests. *(`run_recorder.py` — collision-safe run dirs, immutable resolved config, atomic best/last checkpoints with architecture-compatibility checks, per-epoch JSONL metrics, run manifest with initialized/running/completed/failed status + captured exception details.)*

**Technical acceptance passed** — see IMPLEMENTATION_STATUS.md for the full account, the one-command offline smoke test (`python -m plantaox.c2_pu.run fr4-infra-smoke-test`), and the explicit note that this is infrastructure only, not a trained PN/PU baseline (Task 4.2+).

## 4.2 — PN Baseline Implementation
- [x] Implement PN classifier using E1 positives and **C1 assumed negatives**. *(`pn_baseline.py`: `select_positive_evidence_tier` filters to E1 only; `split_c1_train_validation` partitions C1 deterministically; `PnDataset` structurally excludes C2/C3/external control.)*
- [x] Connect shared fused representation and frozen partitions. *(Reuses `BinaryMlp`/`build_experiment_data()` directly — 495-dim fused features, GraphPart fold-0 held-out positives untouched.)*
- [x] Run monitored training and validation. *(`train_pn_baseline()`: BCE-with-logits, per-epoch train/val loss, non-finite feature/logit/loss/gradient checks, optional early stopping on validation loss only.)*
- [x] Confirm probability inference and checkpoint loadability. *(Fresh `BinaryMlp` reloaded from `checkpoint_best.pt` via Task 4.1's compatibility-checked loader; `predict_proba()` verified bounded/finite on real validation rows.)*
- [x] Save initial results and learning curves. *(`fr4_pn_baseline_fold0_summary.json` + hand-rolled SVG learning curve, both committed; real fold-0 result: best epoch 3, val loss 0.3138, 14 epochs before early stopping.)*

**Technical acceptance passed (PASS)** — see IMPLEMENTATION_STATUS.md for the full account, real fold-0
training/validation counts, the genuine (non-fabricated) overfitting result, bit-identical same-seed
reproducibility evidence, and the explicit research-limitations section (assumed-negative labels,
shortcut-bias risk, fold-0-only scope, no scientific sign-off implied).

## 4.3 — Plain nnPU Baseline Implementation
- [x] Implement non-negative PU risk estimator and unit tests. *(`nnpu_risk.py::compute_nnpu_risk` — direct-clamped `R_nnPU = pi*R_p^+ + max(0, R_u^- - pi*R_p^-)`, stable `softplus`-based logistic loss; 32 unit tests in `test_nnpu_risk.py` verifying manual reference values, the positive/negative-risk-clamp branches, a deliberately-constructed zero-boundary case, gradient sign/zero-at-clamp, prior validation, numerical stability, per-group-mean semantics, and empty-batch rejection.)*
- [x] Prepare labeled E1/E2 positives and unlabeled samples correctly. *(`nnpu_baseline.py`: `select_e1_e2_positive_evidence` pools E1+E2 (excludes any E3) while preserving per-row tier provenance; C1 reused as UNLABELED via `pn_baseline.split_c1_train_validation` unchanged — never relabeled negative. Real fold-0 counts: 331 E1 + 273 E2 = 604 train, 48 E1 + 58 E2 = 106 validation, 3,220 C1 train / 568 C1 validation.)*
- [x] Choose/document initial positive-class prior π and its limitations. *(`DEFAULT_PRIOR=0.10`, explicitly PROVISIONAL — no pre-specified prior found anywhere in the project docs (verified directly); `PRIOR_SENSITIVITY_GRID=(0.05,0.10,0.20)` defined, full sensitivity training deferred; `PRIOR_PROVENANCE_NOTE` recorded in every run's resolved config/summary.)*
- [x] Train C1-only nnPU with no curriculum. *(`train_nnpu_baseline()`: paired positive/C1-unlabeled mini-batches via a cycling sampler, direct-clamped nnPU risk, non-finite feature/logit/risk/gradient checks, early stopping on validation nnPU risk only — no C2/C3/curriculum staging anywhere.)*
- [x] Validate loss stability and inference output. *(Per-epoch risk-component + clamped-fraction logging; `stability_diagnostics` reports clamping frequency, prediction saturation, and divergence — a genuine, reported finding: ≈98-100% of updates were clamped in every epoch of the real fold-0 run, documented not hidden. Fresh `BinaryMlp` reloaded from `checkpoint_best.pt`; `predict_proba()` verified bounded/finite on real validation rows.)*
- [x] Save trained model, logs, and configuration. *(`fr4_nnpu_baseline_fold0_summary.json` + hand-rolled SVG learning curve (reusing PN's generalized plotting routine), both committed; real fold-0 result: best epoch 15, val nnPU risk ≈1.843e-4, 26 epochs before early stopping.)*

**Technical acceptance passed (PASS)** — see IMPLEMENTATION_STATUS.md for the full account, real fold-0
E1/E2/C1 counts and training/validation results, the genuine (non-fabricated) persistent-clamping
stability finding, bit-identical same-seed reproducibility evidence (history and underlying checkpoint
weights), the explicit nnPU-variant identification (direct-clamped, not the beta/gamma corrective
procedure), and the full research-limitations section (provisional prior, E2 provenance, positive-
selection bias, nnPU-vs-PN loss incomparability, fold-0-only scope, no scientific sign-off implied).

**POST-ACCEPTANCE DIAGNOSTIC (2026-10-15), not a reopening of Task 4.3's PASS status:** the ≈98-100%
negative-risk-clamping finding above was investigated via a controlled π ∈ {0.05, 0.10, 0.20}
sensitivity experiment (fold 0, all else held constant — same E1+E2/C1 partition, architecture, seeds).
Result: clamping is **persistently near-universal across all three priors** (mean per-update clamped
fraction 0.982–0.992), i.e. NOT resolved by retuning π within this grid, though C1 prediction scores
do shift materially with π (median C1 score ≈0.006 at π=0.05 vs ≈0.298 at π=0.20). See
`FR4_NNPU_PRIOR_SENSITIVITY_DIAGNOSTIC.md` for the full report, figures, and recommendation. The
accepted π=0.10 baseline and all frozen upstream artifacts were verified byte-unchanged throughout.
Recommendation: a separately-scoped beta/gamma corrective-nnPU comparison (Variant A vs Variant B) is
proposed as a follow-up, not implemented here — Task 4.4 is not blocked on it.

## 4.4 — Additional PU Baselines
- [x] Install/test PULearn-compatible dependencies. *(`pulearn==0.2.0` installed into `.venv` and
  verified against a tiny synthetic P-vs-U example (`ElkanotoPuClassifier`, `WeightedElkanotoPuClassifier`,
  `BaggingPuClassifier`) BEFORE use on real data; works cleanly against the already-installed
  scikit-learn 1.9.0. Both now declared in `requirements.txt`.)*
- [x] Implement Two-Step PU. *(`two_step_pu_baseline.py`, Elkan & Noto 2008-style, via
  `pulearn.ElkanotoPuClassifier` wrapping `sklearn.linear_model.LogisticRegression`. Real fold-0 result:
  estimated correction constant `c ≈ 0.7085`; the `1/c`-corrected estimate exceeds 1.0 for 12.0% of
  validation rows, a documented property of the Elkan & Noto estimator itself, not a bug.)*
- [x] Implement PU-Bagging. *(`pu_bagging_baseline.py`, Mordelet & Vert 2014-style, via
  `pulearn.BaggingPuClassifier` wrapping the same `LogisticRegression` base estimator, `n_estimators=100`.
  Real fold-0 result: `oob_score_ ≈ 0.795`; confirmed directly from pulearn's source that only C1 rows
  are bootstrap-resampled (positives are fixed in every bootstrap member), so all 604 training positives
  structurally have zero valid out-of-bag observations -- verified on real data, documented not hidden.)*
- [x] Use comparable partitions/features and document algorithm differences. *(`pu_sklearn_common.py::
  build_sklearn_pu_dataset` reuses Task 4.2/4.3's exact E1+E2 positive selection and
  `split_c1_train_validation` C1 partition unchanged -- real fold-0 counts match Task 4.2/4.3 exactly
  (604/106 positives, 3,220/568 C1). Algorithm-difference documentation lives in each baseline module's
  own docstring and the `IMPLEMENTATION_STATUS.md` Task 4.4 entry: base-estimator family (sklearn
  LogisticRegression, not `BinaryMlp`), training procedure (single non-iterative `.fit()`, no epoch loop,
  no learning curve), no explicit prior/correction-constant equivalent for PU-Bagging, and no
  BCE/nnPU-risk framework for either.)*
- [x] Save baseline artifacts and configs. *(Committed summaries `fr4_two_step_pu_baseline_fold0_
  summary.json` / `fr4_pu_bagging_baseline_fold0_summary.json` + provenance JSONL logs; `joblib`
  checkpoints gitignored under `data/interim/c2_pu/fr4_two_step_pu_baseline_runs/` /
  `fr4_pu_bagging_baseline_runs/`, SHA-256-recorded in each summary.)*

**Technical acceptance passed (PASS)** — see IMPLEMENTATION_STATUS.md for the full account: real fold-0
counts, the base-estimator decision and its rationale, the documented Two-Step PU out-of-range-probability
and PU-Bagging never-out-of-bag-positives properties (both verified on real data, not assumed), checkpoint
save/reload reproducibility, full research-limitations section, and the explicit statement that MCC/AUPRC
and a cross-baseline comparison table are Task 4.5's scope, not performed here.

## 4.5 — Initial Model Evaluation and Testing
- [x] Run reduced-data one-fold PN smoke test.
- [x] Run reduced-data one-fold nnPU smoke test.
- [x] Test additional PU baselines where implemented.
- [x] Verify MCC and AUPRC calculations on labeled/assumption-based sets as appropriate.
- [x] Check probability bounds, NaN/Inf, stability, and checkpoints.
- [x] Generate a clearly labeled preliminary comparison table.

**Technical acceptance passed (PASS), 2026-10-15.** Existing Task 4.2–4.4 smoke/training evidence was
reused and all five accepted best checkpoints were reloaded for a common, inference-only fold-0
evaluation. The primary comparison uses 124 GraphPart-held-out positives and 38 assay-inactive external
controls at a fixed 0.5 threshold. C1/C2/fold-0 C3 results remain separately labeled as unlabeled
descriptions or assumed-negative proxies. Two-Step PU raw corrected scores are retained while bounded
copies are used for threshold/Brier metrics. See `FR4_BASELINE_EVALUATION_REPORT.md`; no Task 4.6 work
was performed.

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
purpose, annotated with where the evidence lives.** Technical acceptance evidence for every line below
is in `fr2_acceptance_report.md` (frozen as `pp2_baseline_v1`, 2026-10-14) — checking these here would
again conflate "the pipeline is correct and reproducible" with "a supervisor reviewed and approved it."
- [ ] C1 has **5,000 verified records**, with source, seed, and screening log. *(5,000 records (3,788 unique), reproducible from seed 42, 0 overlap against FR1 positives/conflicts/C2/C3 — canonical `stage_c1_decoys_v3.fasta`, §2-3 of fr2_acceptance_report.md. All known issues resolved: alphabet policy (§Known Issue #9/#10) and cross-pool overlap (Decision A) both fixed.)*
- [ ] C2 has approximately **2,000 curated bioactive unlabeled** records. *(exactly 2,000, built from Peptipedia v2.0, canonical `stage_c2_bioactive_unlabeled_v2.fasta` after Decision B's homology-to-positive fix; AODB/DFBP cross-reference still outstanding, Known Issue #15 — not blocking this count)*
- [ ] C3 has **2,000 ESM-2-nearest unlabeled** candidates with ranked distances. *(2,000 per fold, fold-safe by construction, formally re-verified for all 5 folds — 2,325 unique sequences in the exported union; AODB/DFBP cross-reference still outstanding, Known Issue #15 — not blocking this count)*
- [ ] AOP exclusion and pool overlap audits documented. *(complete for all pairs — FR1 positives/179 conflicts/C1/C2/C3/external control — `fr2_acceptance_report.md` §3-4; 11 residual C1↔C2 near-duplicate families accepted as a documented, project-owner-approved limitation)*
- [ ] Length, composition, and descriptor checks included. *(Task 2.5 — `fr2_acceptance_report.md` §7: every pool differs significantly from positives on length/MW/charge/GRAVY/aromaticity, quantified via KS-test, not just plotted)*
- [ ] External experimentally inactive controls remain separate and verified. *(38-record external control validated against the frozen baseline, zero exact overlap, zero genuine homology (EMBOSS needleall, not CD-HIT) against FR1 positives — `anoxpepred_external_control_validated.csv`, `fr2_acceptance_report.md` §8)*
- [ ] Pool versions, generated artifacts, and regeneration commands frozen. *(`pp2_baseline_v1`, 28 files, checksummed manifest, `pp1_baseline_v1` confirmed untouched)*

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
