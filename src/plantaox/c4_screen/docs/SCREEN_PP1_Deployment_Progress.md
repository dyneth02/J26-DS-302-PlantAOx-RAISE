# Component 4 (PlantAOP-Screen) Deployment Progress

**Status snapshot:** 19 October 2026  
**PP1 presentation target:** 21 October 2026 (supersedes the 26 October draft date)  
**Scope:** Repository evidence available at this snapshot; status is not supervisor approval.

## Summary

| Workstream | Status | Evidence / gap |
|---|---|---|
| Documentation architecture | Done | Component README, architecture, methodology, data/output contracts, and validation criteria are present in `src/plantaox/c4_screen/docs/`. They explicitly distinguish planned methodology from current implementation. |
| Repository scaffold | Done for Gate 1 | Implemented `digest.py`, `filters.py`, `dedup.py`, `descriptors.py`, `run.py`, `config.yaml`, and focused tests in the established `src/` and `tests/` layout. Embedding/AD/signal modules remain out of this scope. |
| Proteome inputs | Done for Gate 1 | Four unchanged reviewed FASTAs are in `data/raw/c4_screen/proteomes/`; original UniProt-named downloads are retained under `source_downloads/`. URL, access date, file size, SHA-256, release, and counts are in `metadata/c4_data_registry.csv`; exclusions are in `metadata/c4_protein_exclusions.csv`. |
| Dependencies and environment | In Progress | The requested fair-esm, biopython, pyteomics, pandas, pyarrow, scikit-learn, and pytest packages are installed in `.venv`, and `requirements.txt` now records the environment via `pip freeze`. CUDA is unavailable (`False`); the ESM-2 download remains incomplete and model loading is not verified. `tests/c4_screen/check_gpu.py` is a probe, not a pipeline acceptance test. |
| Candidate generation (FR1 / Gate 1) | Done | `python -m plantaox.c4_screen.run all` generated candidate Parquet/FASTA, membership, funnel, and funnel-only summary. Five focused tests pass. A repeated full run produced byte-identical SHA-256 values for all nine outputs. All 152,259 sequences are unique and all 266,361 parent-coordinate provenance links were checked against the source FASTAs. Optional BIOPEP web comparison and C1/C2 handoff remain pending. |
| Embeddings and AD tiers (FR2) | In Progress; handoff supplied, validation pending | User reports all five Colab handoff files are now in `data/interim/c4_screen/embeddings/`. The ordered production stages and full-data diagnostics are pending this run; prior no-input status below is superseded. No local ESM-2 execution. |
| PDSS (FR3) | Pending | No implementation or results. Planned stretch/later analysis. |
| Signal integration and combined score (FR4) | In Progress; synthetic contract verified | Existing mock utility is reused; sequence joins preserve source labels; score formula and Tier 3 zeroing are implemented and tested synthetically. No real signal files exist, and no retrieval metrics are computed on mock signals. |
| Cross-predictor audit (FR5) | Pending | No implementation or predictor outputs are present. Later milestone. |
| Retrieval evaluation (FR6) | Pending | No held-out evaluation set, metric implementation, or results are present. Later milestone. |
| Evidence cards (FR7) | In Progress; synthetic contract verified | JSON top-50 and abstained-list card generation, C4-provisional BCS flags, provenance fields, and mock notices are implemented and tested synthetically; no real cards are generated. |
| Dashboard | In Progress; synthetic artifact support | A self-contained, offline HTML dashboard and MOCK-labelled summary generator are implemented and synthetically tested. No dashboard populated with real project results exists. |
| PP1 freeze, report, and presentation | In Progress | Presentation target is 21 October 2026. Full-data checksum freeze and evidence depend on successful ordered production stages and test run. |

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
- The local project environment reports no CUDA device. A first-call ESM-2 weight retrieval was initiated; a successful download/model load is not yet verified.
- The top-level project `README.md` is empty; the Component 4 entry point and command documentation are in `src/plantaox/c4_screen/docs/README.md`.

## Source-document alignment and unresolved decisions

- The PP1 task inventory narrows the near-term target to FR1, FR2, and FR4/FR7 using explicitly labelled dummy C1/C2/C3 signals. FR3 is stretch; FR5/FR6 are later milestones.
- The supplied plain-language overview and Full Analysis V2 describe the proposed end-state, not implemented behavior. Their assumptions must not be presented as results.
- The inventory's safeguards take precedence for the PP1 execution plan where source drafts differ: rule-based pepsin pH 1.3 as a documented BIOPEP-UWM substitute if no batch interface is available; exact-sequence deduplication with provenance; provisional reference cloud explicitly labelled; dummy signals never represented as evaluation results.
- Open scientific decisions include the cloud-distance calibration and `d_norm` definition, the potentially unstable PDSS denominator, BCS warning/strata thresholds, C1 embedding recipe confirmation, and disjointness of reference and held-out sets. Resolve and record before treating resulting numbers as validated.
- The proposal and analysis include target metrics (PARRS, PDSS, ARR, Recall@K, MRR, EF@1%) and novelty statements. They are planned outcomes and claims to validate, not current results.

## Current work session — embedding/AD and mock integration (19 October 2026)

- **Done and unchanged:** Gate 1 candidate generation. The task inventory, provisional interface spec, progress file, Colab notebook, existing mock utility, and project outputs were inspected.
- **Superseded:** The previous snapshot reported five missing Colab handoff files. The project owner now reports they have been supplied; verify them during this run and record actual validation results below.
- **Implemented and synthetically verified:** strict embedding handoff validation; supplied-cloud metadata checks; LOO AD calibration and tiering; diagnostics including mean-centering checks on degeneracy without threshold tuning; existing mock generator/validator integration; sequence-key joins; scoring; cards; MOCK-labelled summary and offline dashboard.
- **Verification:** `tests/c4_screen/test_downstream_pipeline.py` — 7 passed; all `tests/c4_screen` tests — 12 passed. These tests use synthetic fixtures only and do not establish real-data metrics or full-corpus outputs.
- **In Progress:** Run `embed-import`, `cloud`, `ad`, `signals`, `score`, `cards`, and `dashboard` in order; then run tests and produce the checksum manifest.
- **Constraint:** Layer-33 mean-residue pooling remains a C4 assumption pending C1 confirmation. Reference cloud source is `mock_cloud`; signals are `mock`. No PARRS, Recall@K, MRR, EF@1%, ARR, or PDSS results are claimed.

## Next actions

1. Validate supplied embedding/cloud files and run production stages in order.
2. Run the full test suite and create the output checksum manifest.
3. Keep every mock signal/cloud output visibly labelled and exclude mock data from retrieval-performance metrics.

## Status rule

Use **Done** only when the inventory's defined output and acceptance evidence are present and verified. **In Progress** means a partial artifact exists but acceptance is incomplete. **Pending** means there is no implementation/output evidence or the work is explicitly later scope. Update this file and the task inventory together when status changes.
