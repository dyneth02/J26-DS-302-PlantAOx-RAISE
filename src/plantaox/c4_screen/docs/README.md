# PlantAOP-Screen (Component 4)

Component 4 generates peptide candidates from four reviewed plant proteomes, imports supplied ESM-2 embeddings, assigns applicability-domain tiers, and demonstrates signal integration, ranking, abstention and evidence cards. The current PP1 production cloud and C1/C2/C3 signal inputs are MOCK. Scores and cards are a software demonstration, not biological evidence.

**Snapshot:** 19 October 2026 · **PP1 presentation:** 21 October 2026 · **Freeze ID:** `c4_pp1_freeze_v1`.

## Documentation

| Folder | Contents |
|---|---|
| [`planning/`](planning/) | Task inventory, deployment progress, status, verified PP1 numbers, and decision log |
| [`contracts/`](contracts/) | Provisional C4 interface specification |
| [`technical/`](technical/) | Architecture, methodology, data/output contracts, validation, and checksums |
| [`reports/`](reports/) | Technical report, freeze/handover evidence, and FR1/FR2/FR4/FR7 acceptance reports |
| [`presentation/`](presentation/) | Demo script, slide content, logbook draft, and candidate FASTA handoff draft |

Start with [`planning/PP1_STATUS.md`](planning/PP1_STATUS.md) for verified status and [`planning/PP1_NUMBERS.md`](planning/PP1_NUMBERS.md) for slide-ready values. Detailed methods and contracts are in [`technical/SCREEN_PP1_Methodology.md`](technical/SCREEN_PP1_Methodology.md) and [`technical/SCREEN_PP1_Data_and_outputs.md`](technical/SCREEN_PP1_Data_and_outputs.md).

## Current verified pipeline

- **FR1:** Swiss-Prot reviewed proteomes; pyteomics sequential `pepsin ph1.3` → `trypsin`; 3–20 AA, standard alphabet, at least two amino-acid types, exact-sequence dedup with parent provenance.
- **FR2:** 152,259 candidate sequences imported as 1,280-D ESM-2 vectors (Colab-produced handoff); AD calibration and tiers currently use a 500-sequence synthetic `mock_cloud`. Layer-33 mean residue pooling is a C4 assumption pending C1 confirmation.
- **FR4/FR7:** signals join on sequence and carry their source; default `CS=0.5·SIM_C1 + 0.5·PROB_C2·(1−d_norm)`; Tier 3 is forced to CS=0 and abstained. Current signal files are `source=mock`.
- **Outputs:** candidate tables, tier/ranking tables, cards, summary, diagnostics, offline dashboard and output checksum manifest are under `data/interim/c4_screen/` and are not committed.

## Run from PowerShell at repository root

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m plantaox.c4_screen.run all --reuse-inputs --signals mock
.\.venv\Scripts\python.exe -m pytest tests/c4_screen -q
Start-Process .\data\interim\c4_screen\c4_dashboard.html
```

`--signals dummy` aliases `mock`. `--reuse-inputs` keeps the verified Gate 1 candidate tables and reruns downstream stages. No local ESM-2 weights are required. The real-positive cloud candidate list is documented in [`planning/decision_log.md`](planning/decision_log.md); it has not been embedded, so production remains on `mock_cloud`.

## Scope and limitations

The interface spec is provisional where marked; do not attribute proposed schemas or cutoffs to C1/C2/C3. Mock signal rankings are not classifier performance or biological evidence. Real-cloud embeddings, BIOPEP comparison, local benchmark, chunked checkpointing, C2 fold-0 score integration, PDSS and presentation rehearsal remain pending or deferred as described in the inventory. No repository-wide test suite was run.
