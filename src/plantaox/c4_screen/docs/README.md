# PlantAOP-Screen (Component 4)

Component 4 generates peptide candidates from four reviewed plant proteomes, imports supplied ESM-2 embeddings, assigns applicability-domain tiers, and demonstrates signal integration, ranking, abstention and evidence cards. The current PP1 production cloud and C1/C2/C3 signal inputs are MOCK. Scores and cards are a software demonstration, not biological evidence.

**Snapshot:** 19 October 2026 · **PP1 presentation:** 21 October 2026 · **Freeze ID:** `c4_pp1_freeze_v1`. The technical snapshot has limitations; supervisor review, rehearsal, and real cloud embeddings are not complete.

## Current verified pipeline

- **FR1:** Swiss-Prot reviewed proteomes; pyteomics sequential `pepsin ph1.3` → `trypsin`; 3–20 AA, standard alphabet, at least two amino-acid types, exact-sequence dedup with parent provenance.
- **FR2:** 152,259 candidate sequences imported as 1,280-D ESM-2 vectors (Colab-produced handoff); AD calibration and tiers currently use a 500-sequence synthetic `mock_cloud`. Layer-33 mean residue pooling is a C4 assumption pending C1 confirmation.
- **FR4/FR7:** signals join on sequence and carry their source; default `CS=0.5·SIM_C1 + 0.5·PROB_C2·(1−d_norm)`; Tier 3 is forced to CS=0 and abstained. Current signal files are `source=mock`.
- **Output:** candidate tables, tier/ranking tables, cards, summary, diagnostics, offline dashboard and output checksum manifest live under `data/interim/c4_screen/` and are not committed.

See [`PP1_NUMBERS.md`](PP1_NUMBERS.md) for verified funnel/tier numbers and length diagnostics, and [`PP1_STATUS.md`](PP1_STATUS.md) for real/provisional/mock boundaries.

## Run from PowerShell at the repository root

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m plantaox.c4_screen.run all --reuse-inputs --signals mock
.\.venv\Scripts\python.exe -m pytest tests/c4_screen -q
Start-Process .\data\interim\c4_screen\c4_dashboard.html
```

`--signals dummy` is an alias for `mock`. `--reuse-inputs` preserves the verified Gate 1 candidate tables and skips network proteome download/candidate regeneration while rerunning embedding import, cloud metadata, AD, signals, scoring, cards, dashboard and output manifest. Use plain `all` only when intentionally regenerating the reviewed-proteome candidate pipeline. The generated mock run is deterministic on the same inputs.

No local ESM-2 weights are needed for the current pipeline. Do not download/load the model locally for PP1; Colab provides the embedding handoff. The five handoff files are hashed in `data/interim/c4_screen/c4_output_manifest.json` and remain uncommitted.

## Real-positive cloud staged for Colab

A read-only search found the C2 frozen PP1 CD-HIT representative table. The filtered file `data/interim/c4_screen/embeddings_staging/ref_cloud_sequences_real.csv` contains 912 unique E1/E2 sequences (E1=478, E2=434), standard alphabet, length 3–20. Its source label is `c2_fr1_positives_pp1_baseline_v1 (provisional, read-only use, C1 AOP-BenchPos to replace)`. The file has not been embedded. Keep production on `mock_cloud` until a sequence-aligned real embedding handoff is validated.

## Documentation map

- [`SCREEN_PP1_Architecture.md`](SCREEN_PP1_Architecture.md), [`SCREEN_PP1_Methodology.md`](SCREEN_PP1_Methodology.md), [`SCREEN_PP1_Data_and_outputs.md`](SCREEN_PP1_Data_and_outputs.md), [`SCREEN_PP1_Validation.md`](SCREEN_PP1_Validation.md): architecture, methods, data contracts and validation.
- [`SCREEN_PP1_Task_Inventory.md`](SCREEN_PP1_Task_Inventory.md), [`SCREEN_PP1_Deployment_Progress.md`](SCREEN_PP1_Deployment_Progress.md): task evidence and current status. Supervisor acceptance boxes remain separate and unchecked.
- [`C4_PP1_TECHNICAL_REPORT.md`](C4_PP1_TECHNICAL_REPORT.md), [`C4_PP1_FREEZE_REPORT.md`](C4_PP1_FREEZE_REPORT.md), [`C4_PP1_HANDOVER.md`](C4_PP1_HANDOVER.md), [`C4_PP1_FREEZE_MANIFEST.json`](C4_PP1_FREEZE_MANIFEST.json): freeze evidence and integrity record.
- [`c4_fr1_acceptance_report.md`](c4_fr1_acceptance_report.md), [`c4_fr2_acceptance_report.md`](c4_fr2_acceptance_report.md), [`c4_fr4_acceptance_report.md`](c4_fr4_acceptance_report.md), [`c4_fr7_acceptance_report.md`](c4_fr7_acceptance_report.md): requirement acceptance evidence.
- [`C4_PP1_DEMO_SCRIPT.md`](C4_PP1_DEMO_SCRIPT.md), [`C4_PP1_SLIDES.md`](C4_PP1_SLIDES.md), [`C4_PP1_LOGBOOK_DRAFT.md`](C4_PP1_LOGBOOK_DRAFT.md), [`C4_CANDIDATE_FASTA_HANDOFF.md`](C4_CANDIDATE_FASTA_HANDOFF.md): presentation/handoff drafts; the message is not sent.
- [`decision_log.md`](decision_log.md): scientific/engineering decisions, including mock cloud policy and the staged C2-derived sequence list.

## Scope and limitations

The C4 interface spec is provisional where marked; do not attribute proposed schemas or cutoffs to C1/C2/C3. Do not treat mock signal rankings as classifier performance or biological evidence. The real cloud requires Colab embeddings and validation. The optional BIOPEP comparison, local benchmark, chunked checkpointing, C2 fold-0 score integration, PDSS and presentation rehearsal remain deferred/pending as itemized in the inventory. No repository-wide test suite was run.
