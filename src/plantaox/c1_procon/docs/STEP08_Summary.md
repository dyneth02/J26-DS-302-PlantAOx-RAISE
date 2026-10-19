## 10. Summary

**Date:** 2026-10-18 · **Notebook:** `STEP08_Confound_Controls.ipynb` · **Data:** release `aop_procon_v1` (S2 fingerprint `47d9c2a2fff63eb1`, matches the SHA-256 MANIFEST)
**Pool:** strict, n = 669 (MC-active 104 / FRS-only 565) · **CV:** `StratifiedGroupKFold(5)` × 10 repeats, groups = `homology_group`
**Metric:** fold-mean AUROC (mean of 50 test folds). CI = group bootstrap over homology groups. **Chance reference** = NULL band from 20 noise seeds.

---

## 1. In short: is any mechanism signal left?

**No ESM-2-specific mechanism signal remains after the confound controls.** What remains is a weak **amino-acid composition** difference of AUROC ≈ 0.60, and in the single-source, length-matched set even that is close to the upper edge of the NULL band.

| Question | Answer (fold-mean AUROC) |
|---|---|
| Best model in the strict pool? | **AAC+LEN+SRC = 0.699**, i.e. composition + length + **source** together. ESM-2 650M alone reaches only 0.601. |
| Source alone? | **SOURCE = 0.640**, higher than ESM-2 650M (0.601), 3B (0.588) and 35M (0.605). |
| Adding ESM-2 to AAC+LEN+SRC? | 650M: **+0.001** [−0.040, +0.036]. 150M: +0.043 [−0.028, +0.078]. 3B: **−0.043** (worse). No CI excludes 0. |
| Source confound removed (AnOxPePred-only, 75 vs 565)? | ESM-2 650M 0.653, AAC+LEN 0.603. ΔAUROC = +0.050 [−0.007, +0.088], p = 0.09. Positive in 10 of 10 repeats, but not significant. |
| Length matched as well (AnOxPePred-only + length-matched)? | ESM-2 650M 0.584, AAC+LEN 0.597. **ΔAUROC = −0.013** (> 0 in only 5 of 20 draws). The earlier +0.05 **disappears**. |
| Does more data help? (learning curve) | Most curves are **flat after 50 %**. The AnOxPePred-only ESM-2 curve rises slightly from 75 → 100 % (0.631 → 0.653), but that is still inside the CI. |

👉 **What can be stated in the paper:** *"Under homology-grouped, repeated CV, the best mechanism predictor is a source + composition + length baseline (AUROC 0.70). ESM-2 adds nothing measurable on top of it (Δ ≤ +0.04, CIs include 0; 3B is worse). In a single-source, length-matched subset all representations fall to AUROC ≈ 0.58–0.62, i.e. a weak composition-level difference only."*

---

## 2. What the two confounds really are (correction of N-19)

- **Source:** all 565 FRS-only peptides come from AnOxPePred. All 29 external-literature peptides are MC-active. The exact AUROC of the SOURCE feature is **0.639**.
- **Length:** the statement *"MC 9.4 aa vs FRS 5.8 aa"* is **wrong** (N-21). In the strict pool the mean length is 5.86 (MC) vs 5.75 (FRS). The real confound is **tripeptides**: **42.8 %** of FRS-only peptides are tripeptides, but only **16.3 %** of MC-active peptides. Length-only AUROC = 0.608.
- After length matching (bins 3, 4, 5, 6, 7, 8, 9–10, 11–14, ≥15, FRS:MC = 2:1, tripeptide share 16.3 % in both groups) the LENGTH probe falls to **0.41**, so no length signal is left. (Values below 0.5 are the usual CV "anti-learning" bias of a balanced feature that carries no signal.)

---

## 3. Split design (assessment item 2)

| Design | MC-active / test fold | MC-only / test fold | ESM-2 650M AUROC |
|---|---|---|---|
| `lso_fold` 2-fold (Step 5 retrieval) | 49 / 55 | **0 / 18** | 0.649 / 0.675 |
| `GroupKFold(5)` (Step 5 probe) | 17–28 | 0–7 | released **0.593**; re-run gives 0.602 / 0.655 |
| **`StratifiedGroupKFold(5)` × 10** | **20–21** | 0–9 | 0.601 (repeats 0.568 – 0.631) |

- With the same recipe, a single `GroupKFold` split ranges from **0.593 to 0.655**, depending on the scikit-learn version and the group-id order (N-22). **Do not quote single-split numbers.** Use the repeated fold-mean of Step 8.
- The *pooled* OOF AUROC of Step 5 is biased by the per-fold intercepts (N-22). Example: the exact value for SOURCE is 0.639, but the pooled value lies between 0.55 and 0.67 depending on the split.
- The RANDOM-noise row of Step 5 (0.384) is **a single noise draw** (seed 0, ≈ 3 sd low). The NULL band over 20 noise seeds is: strict **0.512 [0.430, 0.568]**, AnOxPePred-only 0.505 [0.413, 0.585] (N-23).

---

## 4. Limitations (stated honestly)

- The group-bootstrap CIs keep the fitted models fixed and only resample the test peptides, so they are **narrower** than the true uncertainty. Read them together with the NULL band, the repeat range, and the number of repeats in which Δ > 0.
- The spread of the length-matched results is only FRS subsampling variability, not a full CI.
- MC-active n = 104 (AnOxPePred-only 75). This is too little power to detect ΔAUROC differences below 0.05.
- Labels are not verified at assay level (FRS `source_reported` 631). The composition signal may itself be an AnOxPePred curation artefact.

## 5. Outputs (`C1/STEP 08/`)

`step8_probe_strict.csv` · `step8_probe_anoxpepred_only.csv` · `step8_length_matched.csv` (+ `_runs`) · `step8_learning_curve.csv` + `.png` · `step8_delta_esm_over_confounds.csv` · `step8_cv_design.csv` · `step8_fold_composition.csv` · `step8_headline.csv` · `step8_meta.json`

**🎤 Viva:** *"After controlling for source, length (tripeptides) and homology, ESM-2 embeddings tell us nothing about mechanism beyond amino-acid composition. What remains is a weak composition signal of AUROC ≈ 0.6. That is a negative result, but it was tested rigorously and reported together with its controls."*

