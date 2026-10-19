# AOP-ProCon (Component 1) — Progress log, rebuilt for the corrected pipeline (S2 v3, Steps 1–8)

**Project:** J26-DS-302 · PlantAOx-RAISE · Component 01 — AOP-ProCon  **Owner:** Fernando W A A T (IT23144408)
**Written:** 2026-10-18 (new file; replaces the S1-era `progress_log.md`, which is kept only as history and must not be quoted)
**Canonical data:** S2 build v3, fingerprint `47d9c2a2fff63eb1` — 1,389 unique peptides (FRS 565 · FRS;MC 86 · MC 63 · GEN 675), 573 homology groups, strict-evidence pool 669 (104 MC-active / 565 FRS-only).

> Rule for this log: **every number below was produced by a notebook that ran on Colab (or a local replay that matched Colab to the third decimal) and is stored in `results/` or `STEP 08/`.** Numbers from the S1-era log (0.54 → 0.83, 82 % / 18 %, "homology-safe 0.8", Tier-2 R@5 0.84 …) are retracted.

---

## 1. Where the project stands (one paragraph)
A leak-controlled, multi-label, provenance-tracked benchmark of plant antioxidant peptides was built (Steps 1–3), 15 + 58 positive-only contrastive models were trained and evaluated against untrained baselines (Steps 4–6), and a hash-verified release package with an integration contract was produced (Step 7). The honest result is **negative for the method and positive for the evaluation**: no trained contrastive head beats the untrained ESM-2 embedding, amino-acid composition or length (0 of 25 runs); the supervised probe is weak (fold-mean AUROC 0.61 strict) and is matched by the single feature `source_group` (0.64); ESM-2 adds nothing measurable on top of composition + length + source (Step 8); random folds inflate AUROC by +0.13 … +0.19.

## 2. Timeline

| Date | What happened | Evidence |
|---|---|---|
| ≤ 2026-10-08 | S1-era pipeline (tiers, 1,573 rows) audited; defects E-001 … E-014, N-1 … N-15 found; decision to rebuild as **S2 multi-label** (one row per unique sequence) | `found_errors.md` |
| 2026-10-16 | Step 1 FINAL (S2 build v3, fingerprint fixed), Step 2 FIXED (hard S2 assert, provenance) | S2 CSV, `step1_manifest.json`, `step2_manifest.json` |
| 2026-10-17 – 18 | Step 3 v4 (mode-specific pairs), Step 4 v3 (15 models, collapse report), Step 5 v3 (rewrite), Step 6 (seeds / scale / reverse), Step 7 (release v1); all Colab-verified | `results/step4_* … step6_*`, `release/aop_procon_v1.zip` |
| 2026-10-18 | Honest assessment (≈ 8/10 as a final-year component, ≈ 5.5/10 as research); improvement plan | `C1_Assessment_2026-10-18.md` |
| 2026-10-18 | **New-approach test** (pre-registered): domain-feature probe, SupCon-with-negatives head, tripeptide task | `FIXED_V2/new_approach_2026-10-18/` |
| 2026-10-18 | **STEP 08 confound controls** (source, length, split design, learning curve) → defects N-21, N-22, N-23 | `C1/STEP 08/` |
| 2026-10-18 | Steps 1, 5, 7 **corrected to v4** (repeated grouped CV, SOURCE baseline, null band, new CONTRACT); Step 5 and Step 7 re-run on Colab, identical to the local replay | `FIXED_V2/*.ipynb`, `_backup_before_confound_fix_2026-10-18/` |
| 2026-10-18 | Showcase frontend (Steps 1–8 + Extra) built and updated with the corrected numbers | `FIXED_V2/FRONTEND/` |

## 3. Notebook-by-notebook status

| Step | Notebook (`FIXED_V2/`) | Purpose | Status | Key output |
|---|---|---|---|---|
| 1 | `STEP01_V2_Dataset_Curation_FINAL` | Merge AnOxPePred / Multi-AOP / DFBP / Peptipedia → S2, homology groups, strict evidence, inactive set | Colab-verified; v4 adds a read-only confound cell (do **not** re-run the whole notebook: N-13) | S2 fingerprint `47d9c2a2fff63eb1` |
| 2 | `STEP02_V2_Descriptors_Embeddings_FIXED` | 14 descriptors; ESM-2 35M / 150M / 650M / 3B (max-pool < 10 aa, mean-pool ≥ 10 aa) | Colab-verified, unchanged | SHA-256 of every file |
| 3 | `STEP03_V2_Positive_Pairs_FIXED` | Positive pairs in 3 modes (strict / extended / strict_ge4), percentile + k-NN + random + physchem controls | Colab-verified, unchanged | `pairs/<mode>/*.csv`, `pairs_manifest.json` |
| 4 | `STEP04_V2_Training_FIXED` | 15 contrastive heads (τ 0.2, λ 5, uniformity 1.5), collapse report | Colab-verified, unchanged | `model_*.pt`, `step4_collapse_report.csv` |
| 5 | `STEP05_V2_Evaluation_FIXED` | MC retrieval vs baselines, paired CIs, held-out collapse, **supervised probe (v4)** | Colab-verified v4 | `step5_*.csv`, `step5_probe.png` |
| 6 | `STEP06_V2_Seeds_Scale_Reverse` | 5 seeds, 4 scales, reverse fold | Colab-verified, **does not need re-running** (retrieval only, no Step 5 inputs) | `step6_*.csv` |
| 7 | `STEP07_V2_Release_Package` | Probes as NumPy arrays, `aop_procon.py`, CONTRACT / README / RESULTS_SUMMARY, MANIFEST, zip | Colab-verified v4 (35.2 MB zip, 67 files hashed) | `release/aop_procon_v1.zip` |
| 8 | `C1/STEP 08/STEP08_Confound_Controls.ipynb` | Source / length / AnOxPePred-only / length-matched / learning curve / ΔAUROC of ESM-2 | Local run, 0 errors (needs the release data) | `step8_*.csv`, `step8_learning_curve.png` |

## 4. Verified results (use these, nothing else)

### 4.1 Retrieval (Step 5, strict mode, 49 MC-active queries, chance AP 0.177, chance R@5 0.591)
| representation | AP [95 % CI] |
|---|---|
| LENGTH only | 0.223 [0.209, 0.238] |
| untrained ESM-2 650M | 0.202 [0.192, 0.211] |
| AAC-20 | 0.200 [0.191, 0.211] |
| best trained head (ARI-Checkpoint-Floored) | 0.192 |
| Primary (main model) | 0.140 [0.135, 0.147] |
* Trained vs untrained backbone: **10 of 10 comparisons worse** (paired CI excludes 0). Step 6: **0 of 25** trained runs (5 recipes × 5 seeds) above the untrained embedding; no benefit of scale at 35M / 150M / 650M / 3B; reverse fold direction: only the spread-selected head matches (ΔAP −0.000 ± 0.005), none is better.
* Held-out embedding collapse: 13 of 15 checkpoints have mean cosine > 0.95.
* HP1 (real vs random pairs): ΔAP −0.004 [−0.025, +0.014]; over 5 seeds random pairs are slightly better (−0.014 ± 0.008).

### 4.2 Supervised probe MC-active vs FRS-only (Step 5 v4: 5 folds × 10 fold assignments, fold-mean AUROC; chance = noise null band 0.511 [0.430, 0.567])
| features | strict | extended | strict_ge4 |
|---|---|---|---|
| SOURCE only (`source_group`) | 0.639 | 0.747 | 0.632 |
| LENGTH only | 0.611 | 0.665 | 0.599 |
| AAC-20 | 0.597 | 0.683 | 0.683 |
| ESM-2 650M | 0.606 | 0.671 | 0.600 |
| ESM-2 150M | 0.641 | 0.695 | 0.632 |
| AAC + LENGTH + SOURCE | 0.696 | 0.798 | 0.689 |
| ESM-2 650M + (AAC + LENGTH + SOURCE) | 0.701 | 0.790 | 0.668 |
* ESM-2 650M on top of composition + length + source: **+0.005 [−0.039, +0.041]** (strict); 150M +0.036 [−0.023, +0.070], positive in 10/10 fold assignments but CI includes 0.
* Leakage (leaky random folds minus grouped, strict): **ESM-2 650M +0.186, AAC-20 +0.129**.

### 4.3 Confound controls (STEP 08, strict pool unless stated)
* Source: FRS-only 565 / 565 AnOxPePred; MC-active 75 AnOxPePred + 29 external literature. Exact AUROC of `source_group` alone **0.639**.
* Length: means 5.75 vs 5.86 aa (**not** 5.8 vs 9.4); tripeptide share **42.8 % vs 16.3 %**.
* AnOxPePred-only (75 vs 565): ESM-2 650M 0.653 vs AAC+LEN 0.603, Δ +0.050 [−0.007, +0.088] (not significant); after length matching Δ −0.013.
* Length-matched strict: LENGTH-only 0.41 (matching worked); ESM-2 650M added to confound baseline −0.061.
* Learning curve: flat after ≈ 50 % of the training groups.
* **Verdict: no ESM-2-specific mechanism signal survives; a weak composition-level signal (≈ 0.60) remains.**

### 4.4 New-approach test (pre-registered, exploratory; note: not source-controlled)
* Domain-feature probe (DOM-lite) strict 0.607 vs AAC+LEN 0.616, ESM-2 150M 0.646 → criterion **not met**.
* SupCon head with negatives ≈ logistic regression (AUROC); retrieval AP ≥ raw ESM in 6/6 settings but only 2/6 CIs exclude 0, and it uses labels.
* Tripeptides active vs experimentally validated non-antioxidant: AAC AUROC 0.915 (His/Tyr/Trp/Cys/Arg), but only 10 of 160 inactive tripeptides are conflict-free.

## 5. Decisions taken (and why)
1. **S2 multi-label** instead of tiers: a dual peptide is a legitimate member of both classes (E-006).
2. **Homology groups** (identical sequence ∪ CD-HIT 40 % ∪ ≥ 70 % edit-identity with ≥ 1 peptide ≥ 4 aa), 2-fold split; tripeptides cannot be homology-resolved (V16) — stated limit.
3. **Primary mode = strict**; extended and strict_ge4 are sensitivity analyses.
4. **τ 0.2, λ 5.0, uniformity 1.5** deviate from the TAF (0.07 / 0.1) because the TAF recipe was measured to collapse (Step 4 §3).
5. **Probe metric = fold-mean AUROC over repeated grouped CV** (single split and pooled OOF AUROC are unreliable: N-22).
6. **Report the negative result** instead of tuning until a number looks good; benchmark + audit is the contribution.

## 6. Open work
| Priority | Item |
|---|---|
| PP1 | Slides, `progress_log` HTML, prototype JSON still carry S1-era numbers → update from this file |
| PP1 | Viva Q&A (`help_thesis.md` §9) — rehearse |
| Paper | External validation set (20–30 new literature peptides), cleaner negatives, AnOxPePred-only retrieval re-run |
| Docs | README / CONTRACT already regenerated; check `C1_Assessment_2026-10-18.md` for the 9.4 vs 5.8 aa claim |
| Team | Dyneth's repo convention: branch from `dev`, PR to `dev`, `data/<raw|interim|processed>/c1_procon`, `src/plantaox/c1_procon`, `tests/c1_procon` |

## 7. Reproduction (Colab, `BASE = /content/drive/MyDrive/AOP-ProCon`)
`STEP01` (only the confound cell) → `STEP02` → `STEP03` (**do not re-run**: HP1-Random would become invalid, N-15) → `STEP04` → `STEP05` → `STEP06` → `STEP07`; STEP 08 locally. Every notebook asserts the S2 fingerprint and SHA-256 of its inputs.
