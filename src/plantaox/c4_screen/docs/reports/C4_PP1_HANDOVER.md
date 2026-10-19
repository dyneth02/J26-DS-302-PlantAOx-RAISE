# C4 PP1 Handover

## Frozen snapshot

Freeze ID `c4_pp1_freeze_v1`; local annotated tag `c4-pp1-v2` points to the freeze-doc commit on current branch `feat/c4-Screen1`. The prior `c4-pp1-v1` tag remains unchanged. This is a PP1 technical snapshot with explicit limitations, not supervisor approval.

## Operator quick start (PowerShell)

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m plantaox.c4_screen.run all --reuse-inputs --signals mock
.\.venv\Scripts\python.exe -m pytest tests/c4_screen -q
Start-Process .\data\interim\c4_screen\c4_dashboard.html
```

`--signals dummy` aliases `mock`. `--reuse-inputs` skips network download and FR1 regeneration; it reruns embedding import, cloud metadata, AD, mock signals, score, cards, dashboard and manifest from existing candidate/embedding files. Do not treat successful execution as validation of the mock signals/cloud.

## Read first

1. `PP1_STATUS.md` and `PP1_NUMBERS.md` for verified status and numbers.
2. `C4_PP1_TECHNICAL_REPORT.md` and four `c4_fr*_acceptance_report.md` files for methods and evidence.
3. `C4_PP1_DEMO_SCRIPT.md` and `C4_PP1_SLIDES.md` for presentation draft.
4. `C4_PP1_FREEZE_MANIFEST.json` for checksums/retention and `decision_log.md` for decisions.

## Data and cloud handoff

- Frozen generated outputs are in `data/interim/c4_screen/`; the output checksum list is `c4_output_manifest.json`.
- Five supplied embedding/cloud handoff files remain under `data/interim/c4_screen/embeddings/` and are not committed. Their SHA-256 values are in the output/freeze manifests.
- The staged real cloud file to embed next is `data/interim/c4_screen/embeddings_staging/ref_cloud_sequences_real.csv` (912 rows). Embed its sequences in row order in Colab, export aligned metadata/index and a 912 × 1,280 matrix, then validate source, sequence order/hash, shape and finite values before revising any production tier output. C1 AOP-BenchPos is the intended replacement source if available.
- Draft candidate handoff exists in `C4_CANDIDATE_FASTA_HANDOFF.md`; it has not been sent.

## Integrity and exclusions

Tests verified: `pytest tests/c4_screen` — 15 passed. Two cached full downstream (`all --reuse-inputs`) runs matched all 35 compared generated file hashes. No other-component tests were run. Do not commit `data/`, `.npy`, `.pt`, or model weights. Do not infer biology from mock scores or cards.
