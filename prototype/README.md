# PlantAOx-RAISE — Proposal Prototype

Working prototype for the proposal presentation. Follows the repository's existing
(version 1) monorepo layout, with the frontend switched from Streamlit to React +
TailwindCSS and the addition of a FastAPI backend, per the version-2 architecture note.
Everything under this folder is new; nothing in the rest of the repo or in the sibling
`Research/my` and `Research/dyneth` folders was touched.

## Data source

`data/raw/` is staged from `Research/my/data/`, the canonical, better-organized copy of
this project's datasets (AnOxPePred and Multi-AOP repos, DFBP export, multi-scale ESM-2
embeddings, the processed AOP-BenchPos/descriptors tables). Cross-checked byte-identical
against the earlier Downloads-folder copies for the files that overlap. `Research/my/`
itself was not modified — only read from and copied into this prototype's own `data/raw/`.

## What's real vs. what's a placeholder

Unlike a from-scratch mock, this prototype runs on **real curated data** wherever it was
available locally:

| Component | Real | Placeholder / fallback |
|---|---|---|
| **C1** AOP-ProCon | Curated AOP-BenchPos (1573 seqs, 4 mechanism tiers incl. `Tier_Dual`), 15-feature descriptors, real ESM-2 embeddings at 4 scales with a real PLM-scaling ablation, **and now the real trained positive-only SupCon model** (student's own Google Colab run: real 128-D projection head, real prototypes, real Recall@K/nDCG@10/ARI, real HP1-HP4 significance tests, real 4-model ablation comparison — all independently re-verified against the checkpoints, not copied from the log) | HP5 (retraining the SupCon model itself at each ESM-2 scale) not yet done — the PLM-scaling ablation still uses untrained embeddings for that question |
| **C2** PU-AOP | Real AOP positives, real non-AOP negatives sampled from Peptipedia, real hard-negative selection (standardized-Euclidean nearest to the AOP centroid), real logistic-regression classifier and RNIS/MCC/ECE/Brier metrics | Descriptor-only (no embedding features yet); "easy" negative pool is synthetic random-composition decoys, which is the point of that pool |
| **C3** AOP-BCS | Real sequences, real alanine-scan / BLOSUM62 / random perturbations, audited against **two** real predictors through a shared adapter interface — this prototype's C2 classifier, and a real pretrained external model (Multi-AOP, xLSTM + graph MPNN, loaded from its actual checkpoint) — real IR/FSR/BCS for both | IR/FSR formula is a fixed convention documented in each `bcs_report__*.json` (the source architecture doc left it underspecified) |
| **C4** PlantAOP-Screen | Real digestion (trypsin+pepsin rules) of 25 real reviewed UniProt *Arabidopsis thaliana* antioxidant/defense proteins, real descriptors, real C2 probability, real C3 reliability flag, real PARRS/PDSS/ARR | AD distance uses descriptor space, not ESM-2 embeddings (none computed for fragments); input proteome is a 25-protein subset, not a full multi-species digestome |

Say this plainly to the panel: **curation, descriptors, embeddings (C1), the classifier
(C2), the audit (C3), and the digestion/scoring pipeline (C4) are all real and computed
live from the data.** The only stand-ins are the 2D projection method, the embedding
features for negatives/fragments, and the size of the input plant proteome — all
explicitly called out in each component's `*_summary.json`.

## Layout

```
prototype/
├── data/
│   ├── raw/              # real source data (AOP-BenchPos, descriptors, ESM-2 650M
│   │                      # embeddings, Peptipedia sample, UniProt plant proteome)
│   └── processed/         # aop_sequences.parquet (C1's cleaned/merged table)
├── artifacts/
│   ├── c1/  c2/  c3/  c4/  # generated JSON/parquet artifacts, one folder per component
├── scripts/
│   ├── common_descriptors.py       # shared 15-feature physicochemical descriptor calc
│   ├── generate_c1_artifacts.py
│   ├── generate_c1_scaling_ablation.py  # real PLM-scaling comparison, 35M->3B
│   ├── generate_c1_trained_model_artifacts.py  # real trained SupCon model (see below)
│   ├── generate_c2_artifacts.py    # depends on c1's processed table
│   ├── generate_c3_artifacts.py    # depends on c2's trained model; audits 2 predictors
│   ├── generate_c4_artifacts.py    # depends on c1's table, c2's model, c3's flag
│   └── multiaop_model/             # real pretrained external predictor (see below)
│       ├── aop_def.py, graph_model_def.py   # copied from Research/my/data/raw/Multi-AOP
│       ├── seq_model_def.py        # same, with one CPU-backend fix (see file docstring)
│       ├── features.py             # sequence -> (token ids, molecular graph) builder
│       └── predictor.py            # MultiAOPPredictor: loads the real checkpoint,
│                                    # remaps CUDA->CPU backend weight layout, scores
├── backend/    # FastAPI app serving each component's artifacts as JSON
│   └── app/
│       ├── main.py            # app + CORS + router registration
│       ├── artifacts.py       # generic artifacts/<component>/<file>.json loader
│       └── routers/           # meta.py, c1.py, c2.py, c3.py, c4.py
└── frontend/   # React + TypeScript + TailwindCSS + Recharts
    └── src/
        ├── api/client.ts      # typed API client, one function per backend endpoint
        ├── components/        # Layout (sidebar nav), Card, Banner, StatCard, PageHeader
        └── pages/              # Home, C1Page, C2Page, C3Page, C4Page
```

## Regenerating the artifacts

Run in order (each script depends on the previous one's output):

```bash
cd prototype/scripts
python generate_c1_artifacts.py
python generate_c1_scaling_ablation.py         # optional; needs c1_artifacts run first
python generate_c1_trained_model_artifacts.py  # needs data/raw/trained_model/ (see below)
python generate_c2_artifacts.py
python generate_c3_artifacts.py
python generate_c4_artifacts.py
```

Peptipedia's full 27MB export lives outside the repo (in the Downloads folder it was
generated in); `generate_c2_artifacts.py` reads it once via the `PEPTIPEDIA_CSV`
env var (defaults to `D:\Download\peptipedia_search.csv`) and caches a small sample to
`data/raw/peptipedia_sample.csv`, which *is* committed, so re-runs don't need the original.

`generate_c3_artifacts.py` needs `torch`, `torch_geometric`, `rdkit`, and `xlstm` (all in
`requirements.txt`) to run the real Multi-AOP predictor — CPU-only, no GPU required, but
the audit against it takes roughly a minute.

## Headline numbers (this run)

- **C1**: 1573 curated peptides — Tier1_FRS 565, Tier2_MC 84, Tier3_GEN 858, Tier_Dual 66.
  Tier2_MC is still below the n≥150 target after the full multi-database merge — a real,
  reportable data-sufficiency finding. **Real trained model**: Recall@10 0.9515, nDCG@10
  0.877, ARI 0.104 on the LSO split; HP3 (Tier1 vs Tier2 discriminability) significant with
  a large effect (p=1.8e-36, r=0.878) even after Bonferroni correction — HP1/HP2/HP4 all
  honestly non-significant. Untrained-baseline PLM-scaling ablation (35M→3B) still shows
  purity rising 0.25→0.30 with scale — that comparison (does scale help *the trained model*)
  is Task 6, not yet run.
- **C2**: RNIS ≈ -0.01 (MCC_easy 0.47 vs MCC_hard 0.48) for the descriptor-only baseline —
  say plainly that a full ESM-2-embedding classifier is expected to show sharper inflation.
- **C3**: two real predictors audited with identical perturbations. This prototype's C2
  logistic regression: BCS 0.55 (IR 0.61, FSR 0.10) → **MEDIUM**. The real pretrained
  Multi-AOP model (xLSTM + graph MPNN, reported val accuracy 0.906): BCS 0.48
  (IR 0.55, FSR 0.13) → also **MEDIUM**. Worth leading with: a real, previously-published-
  style predictor with 90%+ reported accuracy still only reaches MEDIUM behavioural
  consistency under this audit — accuracy alone doesn't tell you a predictor is reliable,
  which is the whole thesis of this project.
- **C4**: 350 candidate fragments from 25 real plant proteins; 301 land in AD Tier1;
  PARRS 1.16, PDSS 0.97, ARR 1.0.

## Running the app

Two servers, both read-only over the artifacts generated above — no GPU, no internet
needed once `data/raw/` is populated.

```bash
# Terminal 1 — backend (http://localhost:8000, docs at /docs)
cd prototype/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:5173)
cd prototype/frontend
npm install
npm run dev
```

Open http://localhost:5173 — Home page links to all four component pages
(`/c1` `/c2` `/c3` `/c4`), each fetching its artifacts live from the backend.

## The pretrained Multi-AOP model, and the two bugs fixed to run it on CPU

`Research/my/data/raw/Multi-AOP/predict/` has a real, previously-trained sequence+graph
hybrid model (`best_combined_model.pth`: xLSTM over the sequence, an MPNN over each
residue's amino-acid-as-SMILES molecular graph, reported val accuracy 0.906 at epoch 17).
This is now C3's second audited predictor, via `scripts/multiaop_model/`. Getting it
running on CPU (no GPU on this box was configured for it) required two fixes, both
documented in-place rather than silently patched:

1. **`seq_model_def.py`**: the original hardcodes the xLSTM sLSTM backend as `"cpu"` for
   non-CUDA machines, but the installed `xlstm` package only accepts `"cuda"` or
   `"vanilla"` — `"cpu"` raises `RuntimeError: sLSTMCell unknown backend cpu`. Changed to
   `"vanilla"`, xlstm's actual CPU backend.
2. **`predictor.py`**: the CUDA and vanilla sLSTM backends store the recurrent-kernel
   weight tensor in different physical layouts, so loading a CUDA-trained checkpoint
   straight into the vanilla model fails with a shape mismatch (`[4,32,128]` vs
   `[4,128,32]`). Fixed with the *exact* conversion `xlstm` itself defines and doctests
   between backends (`xlstm/blocks/slstm/cell.py`: `sLSTMCell_cuda` / `sLSTMCell_vanilla`
   ext2int/int2ext) — a lossless layout remap, not an approximation, so inference should
   match the original CUDA run bit-for-bit modulo floating-point associativity.

Batched CPU inference runs at ~45ms/sequence (batch size 32); the full 250-sequence,
4-variant C3 audit against this model takes about a minute. Nothing in `Research/my/` was
modified — the two fixes live only in this prototype's own copies of the model code.

## C1's real trained model (student's own research, integrated here)

`data/raw/trained_model/` holds 8 files pulled directly from the student's own Google Colab
training run (`Research/my/C1/progress_log.md`, Phase 4 / 4v2 / 5 / 5b / 5.3): 5 real
checkpoints (`phase4_model.pt` + 4 ablation variants) and 3 real result CSVs. This is not
this prototype's work — it's the actual Component 1 research, wired in.

**Independently re-verified, not just trusted.** `generate_c1_trained_model_artifacts.py`
recomputes Recall@{5,10,20}, nDCG@10, and ARI from scratch, using the exact LSO-split
methodology (query=fold1, gallery=fold0) and fusion preprocessing (`StandardScaler` +
concatenation) extracted directly from the student's own notebook code — not copied from
the log. Result: HP1-Random, HP2-Fusion's Recall@10/ARI, and Primary-v2-Balanced all
reproduce **exactly**; the rest are within the same floating-point tolerance the log itself
documents for duplicate dual-mechanism sequences. This is about as strong an independent
cross-check as is possible without the original Colab environment.

**One caveat surfaced along the way, worth fixing before submission:** the *notebook files*
in `Research/my/C1/STEP 05/` (`Phase5_Evaluation.ipynb`, `Phase4v2_Phase5b.ipynb`,
`Phase5_3.ipynb`) currently show 0 executed cells / no saved output — only Phase 1-4's
notebooks carry execution proof. The result files now in `data/raw/trained_model/` are real
proof the runs happened, but if a panel opens those specific notebook files, they'll look
blank. Recommend re-running with outputs intact before the viva.

## Status

All four components: real data generated, backend serving it, frontend rendering it,
smoke-tested end to end (every `/api/*` route returns 200, all five pages render with
zero console errors). What's left before the panel presentation is your own judgment
call, not a missing piece: reviewing whether the headline numbers above are the ones you
want to lead with, and deciding whether Tier2_MC's data-sufficiency gap needs more source
merging before demo day.
