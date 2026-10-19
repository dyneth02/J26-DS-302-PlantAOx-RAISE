# PlantAOx-RAISE — Component 04 (PlantAOP-Screen)

## Microsoft Planner Work Breakdown: Progress Presentation 01 (PP1)

**Component:** PlantAOP-Screen — Evidence-Backed Positive-Only Plant Digestome AOP Candidate Retrieval with Applicability-Domain Abstention Tiers  
**Owner:** Cooray Y H (IT23191006)  
**Purpose:** Supervisor-visible tracking of implementation, verification, and PP1 evidence  
**Planning date:** 18 October 2026  
**Execution window:** **2 working days** — Day 1 = Sun 18 Oct, Day 2 = Mon 19 Oct *(20–25 Oct is unscheduled contingency, not planned work)*  
**PP1 presentation target:** 26 October 2026 *(from the project Gantt chart; confirm against the official schedule)*  
**PP1 checklist submission target:** 30 October 2026 *(from the project Gantt chart; confirm against the official schedule)*  
**Primary completion targets:** Function A (FR1 + FR2) and Function B (FR4 + FR7, running on dummy C1/C2/C3 signals)  
**Stretch target:** Preliminary PDSS per plant (FR3), then real fold-0 PROB_C2 from the C2 owner

> **Status convention:** Check a subtask only once its output is verified. Mark an entire Planner task complete only when its documented acceptance evidence is available. This document is a plan, not a claim that any work is already completed.

## Repository Status Audit — 19 October 2026

The inventory was synchronized with repository evidence on 19 October 2026. Gate 1 candidate generation is complete and must remain unchanged. Downstream import is blocked by five absent Colab handoff files: `c4_esm2_t33_650M.npy`, `c4_embedding_index.parquet`, `c4_embedding_manifest.json`, `ref_cloud.npy`, and `ref_cloud_sequences.csv`. Do not run or download ESM-2 locally. Import, cloud metadata, AD, mock integration, score/cards, summary, and static dashboard code now have synthetic verification, but this does not satisfy full-data acceptance. See [`SCREEN_PP1_Deployment_Progress.md`](SCREEN_PP1_Deployment_Progress.md) and [`PP1_STATUS.md`](PP1_STATUS.md) for exact status.

> **Two-day reality check:** This plan needs roughly 11–13 focused hours per day. It is only feasible because the scope is deliberately narrow (see the FR map and the Cut List). If Gate 1 or Gate 2 fails, apply the Cut List immediately rather than extending the window.

## How to Use This in Microsoft Planner

- **Bucket:** Use each of the seven top-level numbered sections below as a Planner bucket.
- **Task:** Create a Planner card for each numbered task (e.g., `3.4 — AD Parameter Fitting`).
- **Subtasks:** Paste the nested checkbox items into the task's **Checklist**.
- **Description:** Include the task's goal, output artifacts, time-box, and FR linkage.
- **Attachments:** Attach commit/PR links, plots, manifests, validation logs, or evidence files.
- **Progress:** Use Not started / In progress / Completed, with assignee and due date. Time-boxes appear as `[D1 AM]`, `[D1 PM]`, `[D1 EVE]`, `[D2 AM]`, `[D2 PM]`, `[D2 EVE]`.
- **Recurring quality work:** Keep logbook and decision-log work recurring rather than closing Bucket 7 early.

## Research Scope and Functional Requirement Map

| Requirement | Proposal definition (abridged) | PP1 priority |
|---|---|---|
| **FR1** | Parse four UniProt Swiss-Prot reviewed plant proteomes; sequential pepsin → trypsin digestion; 3–20 AA, ≥2 unique AA; CD-HIT 90% dedup | **Mandatory (Function A)** |
| **FR2** | ESM-2 (`esm2_t33_650M_UR50D`) embeddings; cosine `d_AD` to the AOP reference cloud; Tier 1/2/3 assignment | **Mandatory (Function A)** |
| **FR3** | Plant Domain Shift Score (PDSS) per proteome; Kruskal-Wallis and Spearman analyses | Stretch: preliminary PDSS values only, no statistics |
| **FR4** | Combined Score `CS = 0.5·SIM_C1 + 0.5·PROB_C2·(1 − d_AD)`; CS = 0 for Tier 3 | **Mandatory (Function B), on dummy signals** |
| **FR5** | Cross-predictor audit: AD-Rejection Rate (ARR) for AnOxPePred and Multi-AOP | Later milestone |
| **FR6** | PARRS, Recall@K, MRR, EF@1% against held-out plant AOPs | Later milestone (needs real signals and the held-out set) |
| **FR7** | Structured evidence cards: provenance, physicochemical data, signals, tier, GREEN/AMBER/RED flag, BCS warning | **Mandatory (Function B), on dummy signals** |

**Source basis:** *Proposal Report – IT23191006* (sections 2.2, 3.1–3.6, 4, 5.2–5.3, 8, 9), the C4 Full Analysis V2, the C4 plain-language explainer, and the C1/C2/C3 analyses. This plan operationalises tasks; it does not assert unverified implementation results.

### Research safeguards and ambiguities to resolve

1. **Proteome scope and candidate-size claim:** The proposal cites reference-proteome IDs (UP000008827, UP000007015, UP000030794) but also says "Swiss-Prot reviewed". These are different sets. Use reviewed entries only and report the actual counts. Olive, rapeseed, and soybean reviewed sets are likely far smaller than the proposal's "5K–50K candidates per plant" estimate. Verify, then correct the claim in the PP1 materials.
2. **Digestion engine:** BIOPEP-UWM is the stated engine, but as far as is known it has no public batch API (verify). Implement the cleavage rules in Python (`pyteomics` Expasy-style rules; its pepsin rules are pH 1.3/2.0, so document 1.3 as the nearest to the proposal's pH 1.2) and spot-check against the BIOPEP-UWM web tool. State this deviation openly.
3. **Pepsin may destroy known AOPs:** Pepsin cleaves around aromatic residues, so sequential pepsin → trypsin digestion can fragment known AOPs rich in W/Y/F. Out of PP1 scope, but log it as a planned recoverability check.
4. **CD-HIT on short peptides:** At 90% identity, a peptide of ≤9 AA must match exactly, so exact-match dedup is equivalent there. Use CD-HIT only for 10–20 AA (check its minimum-length and word-size flags). Keep **all** parent accessions per deduplicated peptide.
5. **Provisional reference cloud:** C1's AOP-BenchPos is not ready. The Stage 0 cloud must be labelled provisional in every output and slide. The cloud and the later held-out plant AOP evaluation set must be **disjoint** (MMseqs2 40%), otherwise evaluation leaks.
6. **Undefined AD details (log supervisor-visible decisions):** (a) μ_cloud/σ_cloud are the leave-one-out `d_AD` distribution of cloud members to the centroid, computed once and frozen; (b) the "normalised `d_AD`" in CS is `d_norm = min(d_AD / (μ+2σ), 1)`; (c) PDSS divides by a near-zero baseline and can explode, so raise this with the co-supervisor.
7. **Dummy signals are not results:** SIM_C1, PROB_C2, and BCS are placeholders. Never report PARRS, Recall@K, MRR, or EF@1% computed on them. Injected "high PROB_C2 but Tier 3" demo cases illustrate a hypothesis, not a finding, and must be labelled as such.
8. **Embedding-recipe consistency:** AD distances use `esm2_t33_650M_UR50D` (1280-D). C2's own classifier uses a different ESM-2 size internally, so PROB_C2 is consumed only as a per-peptide score column and no embeddings are shared with it. Confirm layer and pooling with the C1 owner before embedding anything.
9. **Reverse dependency:** C1 and C2 need C4's candidate FASTA to produce real SIM_C1 and PROB_C2 later. Deliver it early.
10. **BCS is per predictor, not per candidate:** A single number would make every card identical. C3 stratifies BCS by mechanism and length bin, so the dummy table and the card flag are keyed by length bin. Only the BCS < 0.5 warning threshold is in the spec; the HIGH ≥ 0.7 / MEDIUM 0.5–0.7 split is a proposal to confirm with the C3 owner.
11. **Naming consistency:** Use PARRS (not PARSS), BCS (not BSC), and "Tier 1 and Tier 2" for ranked candidates (SO3 in the proposal says "Tier 1 and Tier 3" in error).
12. **Not degenerate by design:** If tiers come out degenerate (almost all Tier 1 or almost all Tier 3), investigate (e.g., embedding anisotropy) and log it. Do not tune thresholds to make the demo look good.

---

# Bucket 1 — Setup, Contracts and Data Acquisition

**Priority:** Mandatory, first 3 hours of Day 1  
**Definition of done:** Working environment, downloaded and checksummed inputs, written inter-component contracts, and logged design decisions.

## 1.1 — Environment and Repository Scaffold `[D1 AM · ~1 h]`
- [x] Check CUDA availability in the project environment (result: `False`, 19 October 2026); verify `fair-esm`, `biopython`, `pyteomics`, `pandas`, `pyarrow`, `scikit-learn`, and `pytest` are installed. `requirements.txt` is generated from the active environment with `pip freeze` and records its installed versions.
- [ ] **Start the `esm2_t33_650M_UR50D` weights download in the background** and verify it loads. The first-call download was initiated but has not completed; no model load is verified.
- [x] Create the Gate 1 package and `tests/c4_screen/` layout in the existing `src/plantaox` structure. Later-stage embed/AD/signals/score/cards modules are out of this task's scope.
- [x] Create `config.yaml`: plants, seed = 42, enzyme order, length filter, w1 = w2 = 0.5, SD multiplier = 1.0, `signals.source: mock`, and C4-provisional BCS flags.
- [x] Add and run the CLI entry point `python -m plantaox.c4_screen.run <stage>` with `download`, `digest`, and `all` stages.
- [ ] Reuse shared utilities (e.g., descriptor extraction, seeding) if the shared repository already provides them; do not duplicate.

## 1.2 — Plant Proteome Acquisition `[D1 AM · ~1 h]`
- [x] Download Swiss-Prot **reviewed** FASTA for Glycine max, Oryza sativa (japonica), Brassica napus, and Olea europaea using taxonomy-filtered `reviewed:true` UniProt queries. Downloaded files and exact URLs are in `SCREEN_PP1_DATA_AND_OUTPUTS.md`.
- [x] Record source URLs, access date (19 October 2026, Asia/Colombo), UniProt release (`2026_03`, released 02 September 2026), file sizes, and SHA-256 checksums in `SCREEN_PP1_DATA_AND_OUTPUTS.md`.
- [x] Count FASTA protein records: soybean 439; rice 4,197; rapeseed 159; olive 110. These are input protein counts and cannot be compared directly with the proposal's 5K–50K post-digestion peptide-candidate estimate; revisit the estimate after the FR1 funnel is measured.
- [x] Apply the input filters: drop proteins < 50 AA and sequences with non-standard residues; log exclusions in `data/raw/c4_screen/metadata/c4_protein_exclusions.csv`.
- [x] Save unchanged UniProt response files under `data/raw/c4_screen/proteomes/source_downloads/` with canonical plant-named copies in `proteomes/`; version their provenance with UniProt release, retrieval date, source query, and SHA-256. Keep raw sequence files local and ignored by Git.

## 1.3 — Inter-Component Contract Sync `[D1 AM · ~45 min]`
- [ ] C1 owner: confirm ESM-2 recipe (layer 33, mean-pool over residues excluding BOS/EOS), reference-cloud file format, and whether an interim AOP-BenchPos file exists.
- [ ] C2 owner: confirm the `c2_prob.parquet` format; ask whether the frozen fold-0 checkpoint can later score C4's candidate FASTA (stretch, must not block).
- [ ] C3 owner: confirm the `c3_bcs.json` schema, length-bin stratification, and flag thresholds.
- [ ] Agree the delivery of `candidates.fasta` from C4 to C1 and C2 owners.
- [ ] Record all agreements in the supervisor decision log.

## 1.4 — Design Decision Log `[D1 AM · ~15 min]`
- [x] Log: reviewed-only proteome scope, pyteomics substitution, pepsin pH 1.3 rule, exact-match dedup policy, and C4-provisional BCS flag thresholds in `docs/decision_log.md`.
- [x] Log: μ_cloud/σ_cloud definition, `d_norm` definition, tier thresholds, and provisional-cloud policy before the embedding/AD stage. Logged as decisions; real parameters remain uncomputed pending inputs.
- [x] Log: PDSS denominator concern for supervisor review before the PDSS stage. Concern recorded; supervisor review remains pending.

**Setup evidence attachments:** environment lockfile, FASTA checksums, protein-count table, contract notes, decision log.

---

# Bucket 2 — Function A (Part 1): Digestome Candidate Generation (FR1)

**Priority:** Mandatory  
**Definition of done:** Per-plant, deduplicated, provenance-traceable 3–20 AA candidate tables with descriptors, tested funnel counts, and a delivered candidate FASTA.

## 2.1 — Sequential Digestion Engine `[D1 AM · ~1.5 h]`
- [x] Implement sequential cleavage using installed pyteomics rule `pepsin ph1.3` followed by `trypsin`; complete cleavage by default with parameterized missed cleavages.
- [x] Record, per fragment: parent accession, 1-based inclusive start/end position, and enzyme path.
- [x] Unit-test a toy protein and verify emitted fragments map to parent positions.
- [ ] Spot-check **one** protein against the BIOPEP-UWM web tool; document any differences. *(Cut-list item if time is short.)*
- [x] Document the BIOPEP-UWM → rule-based substitution in the decision log; the optional one-protein web comparison remains pending.

## 2.2 — Length and Composition Filters `[D1 AM · ~30 min]`
- [x] Keep fragments of **3–20 AA**.
- [x] Require **≥ 2 unique amino-acid types** and the standard 20-residue alphabet only.
- [x] Log funnel counts at every step: proteins → raw fragments → length-filtered → composition-filtered.

## 2.3 — Deduplication with Provenance `[D1 AM · ~45 min]`
- [x] Deduplicate by exact sequence **per plant** and across plants, merging all parent accessions and positions into a provenance list.
- [x] Generate stable peptide IDs (sequence-hash based) and a per-plant membership table.
- [x] Skip CD-HIT and document the <=9 AA exact-match equivalence and deferred 10–20 AA clustering in `docs/decision_log.md`.
- [x] Test provenance aggregation on duplicated sequences from multiple parent proteins.

## 2.4 — Physicochemical Descriptors `[D1 AM · ~30 min]`
- [x] Compute molecular weight, pI, GRAVY, and net charge at pH 7 with Biopython.
- [x] Reject NaN/non-finite descriptor values across generated candidates.
- [x] Test representative peptide descriptor values for finite output.

## 2.5 — Candidate Export, Tests, and Hand-off `[D1 AM · ~45 min]`
- [x] Export per-plant candidate tables (parquet), a combined table, and `candidates.fasta`.
- [x] Export the funnel table and funnel-only `summary.json`.
- [x] Automated tests cover parent-coordinate substring mapping, length/composition rules, duplicate merge/provenance, byte-identical reruns, and mock-signal generation/validation.
- [ ] **Send `candidates.fasta` to the C1 and C2 owners.**

> **Gate 1 (end of D1 AM):** Candidate tables exist for all four plants and tests pass. If not, drop the BIOPEP spot-check and the CD-HIT step and proceed.

**Function A1 evidence attachments:** funnel table, candidate tables/FASTA, test output, digestion deviation note.

---

# Bucket 3 — Function A (Part 2): Embeddings, Reference Cloud and AD Tiering (FR2)

**Priority:** Mandatory  
**Definition of done:** 100% of candidates embedded and assigned Tier 1/2/3 against a labelled provisional reference cloud, with diagnostics and a determinism check.

## 3.1 — ESM-2 Embedding Pipeline `[D1 PM · ~1 h]`
- [ ] Implement batch embedding with `esm2_t33_650M_UR50D`: layer 33, mean-pooled over residue positions, excluding BOS/EOS, fp16.
- [ ] **Benchmark on 2,000 peptides** and extrapolate total runtime before launching the full run.
- [ ] Implement chunked checkpointing so an interrupted run can resume.
- [ ] Write an embedding manifest (model, layer, pooling, dtype, row-ID hash).

## 3.2 — Embed All Candidates `[D1 PM · background]`
- [ ] Run embedding for all four plants as a background job while Tasks 3.3–3.4 are coded.
- [ ] Verify shape (N × 1280), dtype, row order against the candidate table, and absence of NaN/Inf.
- [ ] Cache as `.npy` with a peptide-ID index.

## 3.3 — Provisional Reference Cloud `[D1 PM · ~1 h]`
- [ ] Obtain reference AOP positives by this ladder: (1) C1's interim AOP-BenchPos; (2) C2's frozen curated positives; (3) public sources (DFBP / BIOPEP-UWM / AnOxPePred benchmark positives).
- [ ] Embed the reference positives with the identical recipe.
- [ ] Record N, source, evidence-tier mix, and plant-derived fraction; label the cloud **"provisional"**.
- [ ] Confirm the cloud and the future held-out plant AOP set will be kept disjoint; log the rule.

## 3.4 — AD Parameter Fitting `[D1 EVE · ~45 min]`
- [ ] Compute the cloud centroid.
- [ ] Compute leave-one-out `d_AD = 1 − cos(embed(x), centroid)` for cloud members; derive **μ_cloud** and **σ_cloud**.
- [ ] Freeze the thresholds in `ad_params.json`: t1 = μ + σ, t2 = μ + 2σ.

## 3.5 — Tier Assignment `[D1 EVE · ~30 min]`
- [ ] Compute `d_AD` for every plant candidate.
- [ ] Assign Tier 1 (`d_AD < t1`), Tier 2 (`t1 ≤ d_AD < t2`), Tier 3 (`d_AD ≥ t2`).
- [ ] Wire the SD multiplier ∈ {1.0, 1.5, 2.0} as a parameter; show only the default for PP1.

## 3.6 — Diagnostics and Go/No-Go Gate `[D1 EVE · ~45 min]`
- [ ] Plot `d_AD` histograms: reference cloud vs each plant, with threshold lines.
- [ ] Tabulate tier fractions per plant.
- [ ] If tiers are degenerate, run an anisotropy check (e.g., mean-centering) and log the finding; do not tune thresholds to improve appearance.
- [ ] Record the diagnostic outcome in the decision log.

## 3.7 — Preliminary PDSS (Stretch) `[D1 EVE · ~20 min]`
- [ ] Compute PDSS per plant as defined, labelled "preliminary, provisional cloud".
- [ ] Note the near-zero-denominator risk and the proposed leave-one-out alternative for supervisor review.

## 3.8 — FR1/FR2 Acceptance Tests `[D1 EVE · ~30 min]`
- [ ] 100% of candidates have an embedding and a tier.
- [ ] Determinism: two runs produce identical tiering hashes.
- [ ] Performance: tiering plus later ranking on the largest plant completes in under 5 minutes from cached embeddings (NFR2).
- [ ] Export the AD tier table and the tier/AD sections of `summary.json`.

> **Gate 2 (end of D1):** Tiers exist for every candidate and the histogram looks interpretable. If embedding is too slow, reduce to the largest feasible subset per plant (document it) and continue.

**Function A2 evidence attachments:** embedding manifest, reference-cloud description, `ad_params.json`, tier table, histograms, tier-fraction table, determinism log.

---

# Bucket 4 — Dummy Data and Contract Integration

**Priority:** Mandatory (it is what makes Function B demonstrable)  
**Definition of done:** Deterministic, validated, clearly labelled stand-ins for SIM_C1, PROB_C2, and BCS that can be replaced by real files without code changes.

## 4.1 — Contract Schemas and Validator `[D2 AM · ~1 h]`
- [ ] Define the four contract files:
  - `ref_cloud.npy` + `ref_cloud_meta.csv` (N × 1280 float32; id, sequence, evidence tier, organism, is_plant)
  - `c1_sim.parquet` (`peptide_id`, `SIM_C1` in [0,1], `source`)
  - `c2_prob.parquet` (`peptide_id`, `PROB_C2` in [0,1], `evidence_tier` E1/E2/E3/U, `source`)
  - `c3_bcs.json` (predictor, BCS, IR, FSR, BCS per length bin, version)
- [ ] Implement a validator: 100% `peptide_id` coverage, value ranges, no NaN, embedding dimension 1280, model-name string match.
- [ ] Make the validator fail loudly with a specific message per violation.

## 4.2 — Rule-Based Dummy Signal Generation `[D2 AM · ~1 h]`
- [ ] Compute a rule-based `aop_like` score from redox residues {W, Y, H, M, C}, hydrophobic fraction, and a short-length bonus.
- [ ] Generate `PROB_C2 = sigmoid(2·z(aop_like) + N(0, 0.7))` and `SIM_C1 = rescale(0.5·z(aop_like) + 0.5·z(−d_AD) + N(0, 0.5))`, fixed seed 42.
- [ ] Check pairwise Spearman correlations of about 0.3–0.6 so the CS is not trivially redundant.
- [ ] Set `evidence_tier = U` for novel candidates.

## 4.3 — Demonstration Cases `[D2 AM · ~20 min]`
- [ ] Inject about 10 real Tier 3 candidates with `PROB_C2 ≥ 0.9` to illustrate "high classifier score, still abstained".
- [ ] Tag these rows in the data and in the UI as injected demonstration cases (a hypothesis to test, not a finding).

## 4.4 — BCS Placeholder Table `[D2 AM · ~15 min]`
- [ ] Create a placeholder BCS by length bin (e.g., 3–5 AA: 0.42; 6–10 AA: 0.61; 11–20 AA: 0.78) so LOW, MEDIUM, and HIGH paths are all exercised.
- [ ] Mark the table `source: dummy` and note thresholds pending C3-owner confirmation.

## 4.5 — Synthetic Test Sandbox `[D2 AM · ~30 min]`
- [ ] Generate about 2,000 peptides directly (no digestion) with known planted positives near the cloud for unit tests only.
- [ ] Use it to assert code behaviour (e.g., CS ranks planted positives above random), explicitly **not** as a research result.

## 4.6 — Manifest, Labelling, and Swap-Out Procedure `[D2 AM · ~20 min]`
- [ ] Write `DUMMY_MANIFEST.json` (generator version, seed, file hashes).
- [ ] Ensure every dummy file carries a `source: dummy` column.
- [ ] Document the swap procedure: replace file → set `signals.source: real` → run validator → confirm tiers unchanged and CS changes only through signals.
- [ ] Optional stretch: if the C2 owner can run inference with the frozen fold-0 checkpoint, replace the dummy `c2_prob.parquet` and relabel it "real, fold-0, preliminary".

**Dummy-data evidence attachments:** contract schemas, validator output, generator code and manifest, correlation check, swap procedure.

---

# Bucket 5 — Function B: Combined Score Ranking and Evidence Cards (FR4 + FR7)

**Priority:** Mandatory (on dummy signals)  
**Definition of done:** One command that turns tiered candidates plus signal files into a per-plant ranking, evidence cards, and a summary, with tests.

## 5.1 — Signal Ingestion `[D2 AM · ~30 min]`
- [ ] Implement `signals.py`: join on `peptide_id`; fail loudly on missing rows, out-of-range values, or model-string mismatch.
- [ ] Surface each signal's `source` (dummy/real) through to the outputs.

## 5.2 — Combined Score `[D2 AM · ~45 min]`
- [ ] Compute `d_norm = min(d_AD / (μ + 2σ), 1)`.
- [ ] Compute `CS = w1·SIM_C1 + w2·PROB_C2·(1 − d_norm)` with w1 = w2 = 0.5, weights configurable.
- [ ] Force `CS = 0` for all Tier 3 candidates.
- [ ] Wire the weight sweep (w1 ∈ {0.25, 0.5, 0.75}) as a parameter; show only the default for PP1.

## 5.3 — Ranking `[D2 AM · ~20 min]`
- [ ] Rank candidates within each plant by CS with a deterministic tie-break.
- [ ] Keep Tier 3 candidates in a separate "abstained" list with `CS = 0`.

## 5.4 — Evidence Card Generation `[D2 PM · ~1 h]`
- [ ] Build the top 50 Tier 1/2 candidates per plant as JSON cards containing: sequence; provenance (species, parent accession, enzymes, position); physicochemical summary; SIM_C1; PROB_C2 + evidence tier; AD tier and `d_AD`; GREEN/AMBER flag; CS and rank; BCS flag.
- [ ] Render the BCS flag as `Predictor BCS = X.XX [HIGH/MEDIUM/LOW reliability]`, keyed to the candidate's length bin, with the warning text when BCS < 0.5.
- [ ] Show the RED flag only in the abstained list, not as top-50 cards.
- [ ] Carry the dummy-source labels into each card.

## 5.5 — Function B Tests `[D2 PM · ~30 min]`
- [ ] Tier 3 always yields CS = 0.
- [ ] CS stays within [0, 1].
- [ ] CS decreases as `d_AD` increases when other inputs are fixed.
- [ ] On the synthetic sandbox, CS ranks planted positives above random.
- [ ] Weight sweep runs without error.

## 5.6 — One-Command End-to-End Run `[D2 PM · ~30 min]`
- [ ] `python -m plantaox.c4_screen.run all --signals dummy` produces `cards.json` and `summary.json` from cached embeddings.
- [ ] Confirm a re-run is identical (determinism).

**Function B evidence attachments:** CS implementation, cards JSON, abstained list, test output, end-to-end run log.

---

# Bucket 6 — Frontend and Demo Integration

**Priority:** Mandatory for PP1 presentation  
**Definition of done:** A dashboard that loads the generated JSON, shows pipeline, AD, and evidence-card views, labels dummy data, and runs on the presentation machine.

## 6.1 — Reuse the Existing Dashboard `[D2 PM · ~45 min]`
- [ ] Locate the dashboard built 31 Jul–6 Aug (card grid, filters, tier pie chart, sorting, CSV export) per the logbook.
- [ ] Adapt its input schema to the new `cards.json` / `summary.json`; do not rebuild from scratch.

## 6.2 — Views `[D2 PM · ~2 h]`
- [ ] **Pipeline view:** per-plant funnel (proteins → fragments → filtered → deduplicated → embedded), with real counts shown honestly.
- [ ] **AD view:** `d_AD` histogram with μ+σ and μ+2σ lines; tier donut per plant; optional PCA scatter coloured by tier.
- [ ] **Evidence-card view:** top-50 cards with traffic-light badges and BCS warnings; abstained-candidates tab; CSV export.

## 6.3 — Dummy-Data Labelling `[D2 PM · ~20 min]`
- [ ] Add a permanent "DUMMY DATA" ribbon.
- [ ] Add per-signal provenance chips (e.g., `d_AD: real, provisional cloud`; `SIM_C1: dummy`; `PROB_C2: dummy`; `BCS: dummy`).
- [ ] Mark injected demonstration cases.

## 6.4 — Robustness `[D2 PM · ~45 min]`
- [ ] Load static JSON only; no live ESM-2 inference in the demo.
- [ ] Test on the presentation hardware.
- [ ] Confirm regenerate-then-refresh works in one step.

## 6.5 — Demo Script and Fallbacks `[D2 EVE · ~45 min]`
- [ ] Write a 5-minute flow: problem → funnel → AD histogram and tiers → a top card → an abstained "high PROB_C2, Tier 3" case → roadmap.
- [ ] Capture backup screenshots and a screen recording.

**Frontend evidence attachments:** dashboard build, screenshots, screen recording, demo script.

---

# Bucket 7 — Quality, Documentation and PP1 Milestone

**Priority:** Continuous, then milestone-critical  
**Definition of done:** Reproducible, tagged artifacts; an honest report and slides; delivered presentation; submitted checklist.

## 7.1 — Continuous Quality (Both Days)
- [ ] Commit frequently with meaningful messages; link commits to Planner cards.
- [ ] Keep the decision log current as decisions are made.
- [ ] Write dated logbook entries for both days (activities, obstacles, deviations).
- [ ] Keep tests running after each stage.

## 7.2 — Acceptance Gate and Freeze `[D2 EVE · ~1 h]`
- [ ] Re-run the pipeline from raw inputs and fixed config; confirm identical outputs.
- [ ] Run the full test suite.
- [ ] Write a checksummed manifest of all artifacts and tag the release (e.g., `c4-pp1-v1`).
- [ ] Record achieved candidate counts, tier distributions, and any deviations from the proposal.

## 7.3 — PP1 Technical Report (Short) `[D2 EVE · ~1 h]`
- [ ] Document FR1: proteomes, digestion, filters, dedup, funnel counts, and the engine substitution.
- [ ] Document FR2: embedding recipe, provisional reference cloud, AD parameters, tier distributions.
- [ ] Document Function B: CS definition, `d_norm` decision, evidence-card schema, **dummy-signal disclosure**.
- [ ] State limitations: provisional cloud, dummy signals, reviewed-proteome size, unresolved PDSS denominator.
- [ ] Add an FR-to-artifact traceability table.

## 7.4 — PP1 Slides and Rehearsal `[D2 EVE · ~1 h]`
- [ ] Draft 4–5 slides: gap and motivation; architecture; Function A results; Function B demo; roadmap to January.
- [ ] Present only verified results; show PARRS, ARR, and Recall@K as roadmap, not results.
- [ ] Rehearse once with a timer; schedule a second rehearsal in the contingency window.

## 7.5 — Progress Presentation 01 (Target: 26 October 2026)
- [ ] Deliver the component presentation and live demo (fallback: recording).
- [ ] Capture panel questions and feedback.
- [ ] Prepare answers for likely challenges: why dummy data; whether `d_AD` is circular; pepsin vs known AOPs; where the candidate counts come from.

## 7.6 — PP1 Checklist Submission (Target: 30 October 2026)
- [ ] Compile the official checklist and supporting evidence; validate links.
- [ ] Obtain the supervisor logbook sign-off.
- [ ] Submit by the confirmed deadline and save proof of submission.

## 7.7 — Post-PP1 Transition
- [ ] Replan: held-out plant AOP set (MMseqs2 40%), real C1/C2/C3 signals, PARRS, ARR, Recall@K/MRR/EF@1%, PDSS statistics, ablations.
- [ ] Add the pepsin recoverability check for known plant AOPs.
- [ ] Update the Gantt chart and risk register without silently marking unfinished work complete.

---

# Suggested Two-Day Execution Schedule

*Operational suggestion, not a schedule stated in the proposal. Adjust to actual progress.*

| Window | Work | Bucket / Gate |
|---|---|---|
| **D1 08:00–09:00** | Environment, repo scaffold, start weight and FASTA downloads | 1.1, 1.2 |
| **D1 09:00–10:00** | Contract sync with C1/C2/C3 owners; decision log | 1.3, 1.4 |
| **D1 10:00–13:00** | Digestion, filters, dedup, descriptors, export; send candidate FASTA | 2.1–2.5 → **Gate 1** |
| **D1 14:00–18:00** | Embedding benchmark and full run (background); reference cloud | 3.1–3.3 |
| **D1 18:00–21:00** | AD parameters, tiers, diagnostics, acceptance tests | 3.4–3.8 → **Gate 2** |
| **D2 08:00–10:00** | Contracts, validator, dummy signals, sandbox | 4.1–4.6 |
| **D2 10:00–13:00** | Signal ingestion, CS, ranking, cards, tests | 5.1–5.6 |
| **D2 13:00–17:00** | Dashboard adaptation, views, labelling, robustness | 6.1–6.4 |
| **D2 17:00–21:00** | Demo script, freeze and tag, report, slides, first rehearsal | 6.5, 7.2–7.4 |
| **20–25 Oct** | Contingency: supervisor feedback, polish, second rehearsal | — |
| **26 Oct** | PP1 presentation | 7.5 |
| **30 Oct** | Checklist submission | 7.6 |

## Decision Gates

- **Gate 1 (end of D1 AM):** Candidate tables exist for all four plants and tests pass.
- **Gate 2 (end of D1):** Every candidate is embedded and tiered, and the diagnostic histogram is interpretable.
- **Gate 3 (end of D2 PM):** The dashboard loads real tiers with dummy signals through one command.

## Cut List (apply in this order if behind)

1. Preliminary PDSS (3.7)
2. PCA scatter (keep the histogram)
3. BIOPEP-UWM spot-check (2.1) and CD-HIT step (2.3)
4. Weight and SD-multiplier parameter wiring beyond defaults
5. Dashboard filter/CSV polish
6. Last resort: embed a documented subset per plant and demo one plant live while the funnel table still shows all four

# Supervisor Acceptance Checklist

**These are the supervisor's boxes, left unchecked on purpose.** Technical evidence for each line should be attached in the PP1 report; checking them here would conflate "the pipeline is correct and reproducible" with "a supervisor reviewed and approved it".

## FR1 — Candidate Generation
- [ ] Four reviewed proteomes documented with source, release, counts, and checksums.
- [ ] Digestion engine substitution (rule-based vs BIOPEP-UWM) and pepsin pH 1.3 rule reviewed.
- [ ] Length/composition filters and deduplication policy reviewed; provenance preserved.
- [ ] Candidate counts per plant reported honestly against the proposal's estimate.
- [ ] Candidate FASTA delivered to C1 and C2 owners.

## FR2 — AD Tiering
- [ ] Embedding recipe matches the C1 owner's confirmation.
- [ ] Provisional reference cloud source, size, and limitations documented.
- [ ] μ_cloud/σ_cloud definition and tier thresholds reviewed and frozen.
- [ ] 100% of candidates tiered; tier distribution per plant reported with diagnostics.

## FR4 / FR7 — Function B on Dummy Signals
- [ ] CS definition and `d_norm` normalisation reviewed.
- [ ] Tier 3 forced abstention verified by tests.
- [ ] Evidence-card schema matches the spec; BCS flag thresholds confirmed with the C3 owner.
- [ ] Dummy signals disclosed on every output, slide, and report page.

## Stretch and Claims
- [ ] Do not claim PARRS, ARR, Recall@K, MRR, or EF@1% results; these are roadmap items.
- [ ] Label PDSS values "preliminary, provisional cloud" if shown.
- [ ] Do not present dummy-signal rankings as evidence of retrieval performance.

# Research Deliverable Registry (Recommended)

| Artifact | Suggested filename | Purpose |
|---|---|---|
| Proteome registry | `c4_data_registry.csv` | Sources, releases, counts, checksums |
| Candidate tables | `c4_candidates_{plant}.parquet` | Per-plant deduplicated candidates with provenance |
| Candidate FASTA | `c4_candidates.fasta` | Hand-off to C1 and C2 owners |
| Funnel table | `c4_funnel_summary.csv` | Counts per pipeline step per plant |
| Embedding cache | `c4_esm2_t33_650M.npy` + ID map | Cached 1280-D embeddings |
| Embedding manifest | `c4_embedding_manifest.json` | Model, layer, pooling, dtype, hashes |
| Reference cloud | `ref_cloud.npy` + `ref_cloud_meta.csv` | Provisional AD reference set |
| AD parameters | `ad_params.json` | Centroid, μ, σ, thresholds |
| AD tier table | `c4_ad_tiers.parquet` | Per-candidate `d_AD` and tier |
| Dummy signals | `c1_sim.parquet`, `c2_prob.parquet`, `c3_bcs.json` | Contract-conformant stand-ins |
| Dummy manifest | `DUMMY_MANIFEST.json` | Generator version, seed, hashes |
| Ranking output | `c4_ranking.parquet` | CS and rank per plant |
| Evidence cards | `cards.json` | Top-50 cards per plant plus abstained list |
| Dashboard summary | `summary.json` | Funnel, tier fractions, histogram bins |
| Freeze manifest | `c4_pp1_freeze_manifest.json` | Checksummed release (`c4-pp1-v1`) |
| PP1 report | `c4_pp1_technical_report.md` | Actual status, results, limitations |

*These are suggested names, not mandatory paths from the proposal. Adapt them to the established shared repository contracts; do not create duplicate data artifacts.*

---

## Reference Locations Within the Proposal

- **Section 2.2 / Table 2:** SO1–SO6 and measurable anchors.
- **Section 3:** Methodology, data inputs, baselines (including Stage 0), evaluation metrics, validation strategy.
- **Section 4 / Figures 1–2:** C4 pipeline and overall PlantAOx-RAISE architecture.
- **Section 5.2–5.3:** FR1–FR7 and NFR1–NFR6.
- **Section 8 / Figure 5:** Component 4 Work Breakdown Structure.
- **Section 9 / Figure 7:** Project Gantt chart.
- **Appendix 2:** Logbook, including the earlier dashboard prototype entries.

**Version:** 1.0 — PP1 execution-focused Planner breakdown, two-day window.
