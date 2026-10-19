# Component 4 (PlantAOP-Screen) Deployment Progress

**Status snapshot:** 19 October 2026  
**PP1 presentation target:** 21 October 2026 (supersedes the 26 October draft date)  
**Scope:** Repository evidence available at this snapshot; status is not supervisor approval.

## Summary

| Workstream | Status | Evidence / gap |
|---|---|---|
| Documentation architecture | Done | Component README, architecture, methodology, data/output contracts, and validation criteria are present in `src/plantaox/c4_screen/docs/`. They explicitly distinguish planned methodology from current implementation. |
| Repository scaffold | Done for PP1 scope | Implemented Gate 1 candidate generation and downstream embedding import, cloud metadata, AD tiering, mock-signal integration, scoring, cards, dashboard, and diagnostics in the established `src/` and `tests/` layout. |
| Proteome inputs | Done for Gate 1 | Four unchanged reviewed FASTAs are in `data/raw/c4_screen/proteomes/`; original UniProt-named downloads are retained under `source_downloads/`. URL, access date, file size, SHA-256, release, and counts are in `metadata/c4_data_registry.csv`; exclusions are in `metadata/c4_protein_exclusions.csv`. |
| Dependencies and environment | Done for C4 run | Required C4 dependencies are installed. Local CUDA is unavailable; the validated ESM-2 handoff manifest reports Colab Tesla T4. No local ESM-2 load/download was performed. |
| Candidate generation (FR1 / Gate 1) | Done | `python -m plantaox.c4_screen.run all` generated candidate Parquet/FASTA, membership, funnel, and funnel-only summary. The C4 suite passes 12 tests; two complete runs matched across all 34 files in the generated tree. All 152,259 sequences are unique and all 266,361 parent-coordinate provenance links were checked against source FASTAs. Optional BIOPEP web comparison and C1/C2 handoff remain pending. |
| Embeddings and AD tiers (FR2) | Done against MOCK cloud | 152,259/152,259 candidate embeddings validated; cloud N=500 (`mock_cloud`). `mu=0.0185099002`, `sigma=0.0097886926`, `t1=0.0282985928`, `t2=0.0380872854`. No plant has >95% in one tier; no threshold tuning. |
| PDSS (FR3) | Pending | No implementation or results. Planned stretch/later analysis. |
| Signal integration and combined score (FR4) | Done with MOCK signals | `signals` and `score` completed, joining on sequence; all sources are `mock`; Tier 3 CS is zero. No retrieval metrics are computed on mock signals. |
| Cross-predictor audit (FR5) | Pending | No implementation or predictor outputs are present. Later milestone. |
| Retrieval evaluation (FR6) | Pending | No held-out evaluation set, metric implementation, or results are present. Later milestone. |
| Evidence cards (FR7) | Done with MOCK signals | `cards.json` has top-50 Tier 1/2 candidates per plant, abstained Tier 3 examples, mock source labels, and ten injected rice demo cases. |
| Dashboard | Done with MOCK data | Offline `c4_dashboard.html` and full summary generated from the validated production outputs. |
| PP1 freeze, report, and presentation | In Progress | Presentation target is 21 October 2026. A checksummed manifest covers 33 generated artifacts and SHA-256-only hashes for all five supplied handoff inputs. Two `all` runs matched across 34 compared files (33 artifacts plus the output manifest). C4 diagnostics include Spearman length associations, cloud/candidate length distributions, and a separate mean-centering sensitivity; baseline thresholds/tiers are unchanged. `pytest tests/c4_screen`: 12 passed; no repository-wide suite was run. Slide numbers are in `PP1_NUMBERS.md`. |

## Gate 1 observed funnel

Counts are from the executed deterministic pipeline. `proteins` is after input exclusions; `protein_exclusions` records dropped short/non-standard records. `deduplicated` is the number of unique sequences belonging to that plant after exact cross-plant aggregation.

| Plant | Input proteins retained | Protein exclusions | Raw fragments | Length 3–20 | Composition/alphabet pass | Per-plant exact unique |
|---|---:|---:|---:|---:|---:|---:|
| Soybean | 410 | 29 | 44,028 | 18,869 | 18,843 | 13,468 |
| Rice | 4,180 | 17 | 551,252 | 239,881 | 239,483 | 140,813 |
| Rapeseed | 152 | 7 | 13,992 | 6,356 | 6,343 | 4,910 |
| Olive | 106 | 4 | 3,508 | 1,692 | 1,692 | 565 |

The reviewed inputs contained 4,905 records; 57 were excluded and 4,848 were digested. Composition filtering retained 266,361 peptide-parent records, which deduplicated to 152,259 global peptide sequences. Per-plant counts overlap when one exact sequence is present in multiple plants.

## Verified repository facts

- The C4 Python package is at `src/plantaox/c4_screen/`, and tests are at `tests/c4_screen/`.
- The C4 package now contains the Gate 1 candidate-generation modules and configuration; tests include unit and mock-signal integration coverage.
- Installed pyteomics 5.0.1 rules were verified as `pepsin ph1.3` and `trypsin`; pyteomics `icleave` offsets preserve parent coordinates.
- Four reviewed-only UniProt query results are present with release/query, sizes, and hashes in `SCREEN_PP1_DATA_AND_OUTPUTS.md`; canonical raw files byte-match the downloads.
- The original reviewed input counts were 439 soybean, 4,197 rice, 159 rapeseed, and 110 olive. These are source protein records, not peptide candidate counts.
- The local project environment reports no CUDA device. No ESM-2 weights were downloaded or loaded locally; the supplied Colab embedding handoff was validated and imported.
- The top-level project `README.md` is empty; the Component 4 entry point and command documentation are in `src/plantaox/c4_screen/docs/README.md`.

## Source-document alignment and unresolved decisions

- The PP1 task inventory narrows the near-term target to FR1, FR2, and FR4/FR7 using explicitly labelled dummy C1/C2/C3 signals. FR3 is stretch; FR5/FR6 are later milestones.
- The supplied plain-language overview and Full Analysis V2 describe the proposed end-state, not implemented behavior. Their assumptions must not be presented as results.
- The inventory's safeguards take precedence for the PP1 execution plan where source drafts differ: rule-based pepsin pH 1.3 as a documented BIOPEP-UWM substitute if no batch interface is available; exact-sequence deduplication with provenance; provisional reference cloud explicitly labelled; dummy signals never represented as evaluation results.
- Open scientific decisions include the cloud-distance calibration and `d_norm` definition, the potentially unstable PDSS denominator, BCS warning/strata thresholds, C1 embedding recipe confirmation, and disjointness of reference and held-out sets. Resolve and record before treating resulting numbers as validated.
- The proposal and analysis include target metrics (PARRS, PDSS, ARR, Recall@K, MRR, EF@1%) and novelty statements. They are planned outcomes and claims to validate, not current results.

## Current work session — embedding/AD and mock integration (19 October 2026)

- **Production stages:** `embed-import`, `cloud`, `ad`, `signals`, `score`, `cards`, `dashboard` completed in order. Import validated the manifest hash and exact candidate/index peptide_id+sequence order. Hash uses SHA-256 of newline-joined sequences in index order, matching the manifest recipe.
- **Counts:** 152,259 candidates embedded; zero unembedded. Cloud N=500, `source=mock_cloud`. Signal inputs and BCS have `source=mock`.
- **AD:** `mu=0.0185099002`, `sigma=0.0097886926`, `t1=0.0282985928`, `t2=0.0380872854`. Highest single-tier fraction is rice Tier 1 at 56.99%; no plant exceeds 95%. The requested joint mean-centering sensitivity was run separately; baseline tiers and thresholds were not changed or tuned.
- **Artifacts:** AD tiers, parameters, diagnostics, cloud metadata, mock signals/manifest, ranking, cards, summary, offline dashboard, and the output checksum manifest (33 generated files plus five handoff-input SHA-256 values) exist under `data/interim/c4_screen/`.
- **Verification:** only `pytest tests/c4_screen` was run: 12 passed. No full repository suite was run in this work session.
- **Constraint:** Layer-33 mean-residue pooling remains a C4 assumption pending C1 confirmation. The reference cloud is MOCK; signal results/cards are mock demonstrations, not biological evidence. No PARRS, Recall@K, MRR, EF@1%, ARR, or PDSS results are claimed.

## Next actions

1. Confirm C1's ESM representation recipe and supervisor review of the unresolved PDSS denominator.
2. Preserve the MOCK provenance and prevent mock signals/cloud from being presented as biological evidence.
3. Keep every mock signal/cloud output visibly labelled and exclude mock data from retrieval-performance metrics.

## Status rule

Use **Done** only when the inventory's defined output and acceptance evidence are present and verified. **In Progress** means a partial artifact exists but acceptance is incomplete. **Pending** means there is no implementation/output evidence or the work is explicitly later scope. Update this file and the task inventory together when status changes.


## Current work session — C4 backend API (19 October 2026)

| Workstream | Status | Evidence / next step |
|---|---|---|
| Read-only C4 API and fixture tests | In Progress | Implementing as `backend.app.api.v1.c4_screen`, with component service/schemas and `tests/backend/c4_screen/`; fields are being mapped from the actual frozen parquets and JSON under `data/interim/c4_screen/`. Verification will use the focused fixture-backed API suite. |
