# help_thesis.md — AOP-ProCon (Component 1): how to write and defend the thesis (rebuilt 2026-10-18)

Replaces both old `help_thesis` files (S1-era; their §§1–11 are superseded and must not be quoted — found_errors N-6).
Everything here is tied to the corrected pipeline: S2 build v3, fingerprint `47d9c2a2fff63eb1`, Steps 1–8. Numbers come from `results/` and `STEP 08/`; if a number is not in this file, check the CSV before using it.

---

## 1. The thesis in five sentences (Sinhala + English)
1. Plant antioxidant-peptide data come from several databases with different evidence levels, so I built a **leak-controlled, multi-label (FRS / MC / FRS;MC / GEN), provenance-tracked benchmark** (S2: 1,389 peptides, 573 homology groups).
2. I tested whether a **positive-only contrastive head on frozen ESM-2** adds mechanism information: **it does not** — 0 of 25 trained runs beat the untrained embedding, composition or length.
3. A **supervised probe** (MC-active vs FRS-only) is weak (fold-mean AUROC 0.61, strict), and the single feature **source** gets 0.64; with source, tripeptide share and homology controlled, **ESM-2 adds nothing measurable**.
4. **Evaluation matters:** random splits inflate AUROC by +0.13 … +0.19, one grouped split moves it by up to 0.06, and a one-draw noise row is not chance.
5. The deliverables are the benchmark, the audit protocol, a reproducible negative result, and a hash-verified release with an honest integration contract for Components 2–4.

## 2. What can be claimed — and what cannot

| Can claim (evidence) | Cannot claim |
|---|---|
| A leak-controlled multi-label benchmark with provenance and conflicts (Step 1, fingerprint) | That the contrastive model works or "learns mechanism" |
| Contrastive heads < untrained ESM-2 / AAC / length: 10/10 paired comparisons, 0/25 seeds, 4 scales, reverse fold (Steps 5–6) | That mechanism-aware pairing helps (HP1: random pairs slightly better, 0/5 seeds) |
| Leakage inflation +0.19 (ESM-2 650M) and +0.13 (AAC-20), strict (Step 5 v4) | The old numbers 0.54 → 0.83, 82 % / 18 %, "homology-safe 0.8", AUROC 0.593 as a standalone value |
| `source_group` alone AUROC 0.639; tripeptide share 42.8 % vs 16.3 %; ESM-2 adds +0.005 [−0.039, +0.041] on top of composition + length + source (Steps 5 v4, 8) | That ESM-2 "encodes" FRS/MC beyond composition; that ESM-2 "learned length" (untested, N-26) |
| No benefit of ESM-2 scale in the probe or in the contrastive head (Steps 5–6) | That scale "does not matter" in general (equivalence was not tested; say "no benefit detected") |
| Held-out embedding collapse (13/15 checkpoints mean cos > 0.95) and that the prototype guard measures prototypes only (N-20) | That "collapse was prevented" |
| The loss uses **no confirmed-negative peptides**; collapse is controlled by label-free uniformity and prototype repulsion (N-18) | That the loss is "negative-free" |

## 3. Chapter plan, with the evidence for each chapter

| Chapter | Content | Source in the repo |
|---|---|---|
| 1 Introduction | oxidative stress, plant peptides, the reliability gap, objectives, the 4-component framework | TAF, deck |
| 2 Related work | AnOxPePred, Multi-AOP, DFBP, BIOPEP-UWM; ESM-2; supervised contrastive learning; homology-aware splitting (CD-HIT, GraphPart); AutoPeptideML | `c1-datasets` notes |
| 3 Data (benchmark) | sources, tiers → S2, evidence levels (strict / extended / ≥ 4 aa), homology groups, split audit, conflicts, inactive set | Step 1, `step1_manifest.json`, `found_errors` E-001…E-006, D-004 |
| 4 Representations | 14 descriptors, ESM-2 at 4 scales, pooling rule (max < 10 aa, mean ≥ 10 aa), integrity hashes | Step 2, `step2_manifest.json` |
| 5 Method | positive pairs (percentile, k-NN, random and physchem controls, 3 modes), loss (alignment + uniformity 1.5 + prototype push-away λ 5, τ 0.2), checkpoint rules, **deviation from TAF** (E-007, sweep) | Steps 3–4, Step 4 §2a–§3 |
| 6 Evaluation protocol | MC retrieval with exact chance, baselines (raw ESM-2, AAC, DESC, LENGTH), paired bootstrap + Wilcoxon + Holm, held-out collapse, **repeated grouped CV probe**, leaky control, null band | Step 5 v4 |
| 7 Results | 7.1 contrastive vs baselines, 7.2 seeds / scale / reverse, 7.3 probe, 7.4 leakage, 7.5 **confound controls**, 7.6 exploratory approaches (domain features, SupCon, tripeptides) | Steps 5, 6, 8, `new_approach_2026-10-18` |
| 8 Release and integration | `aop_procon_v1`, CONTRACT, what other components must not assume | Step 7, `CONTRACT.md` |
| 9 Discussion | why negative (data size, collapse, source/length confounds), what the benchmark is for, threats to validity | §7 below |
| 10 Conclusion and future work | external validation set, cleaner negatives, AnOxPePred-only retrieval re-run, assay-level labels | `progress_log.md` §6 |

## 4. Quotable numbers (strict mode unless stated; fold-mean AUROC, 5 folds × 10 fold assignments; chance = noise null band 0.511 [0.430, 0.567])

| Quantity | Value |
|---|---|
| S2 | 1,389 peptides; FRS 565, FRS;MC 86, MC 63, GEN 675; 573 homology groups; strict pool 669 (104 MC-active / 565 FRS-only) |
| MC retrieval, chance AP | 0.177 (49 queries); LENGTH 0.223, untrained ESM-2 650M 0.202, AAC-20 0.200, Primary 0.140 |
| Probe, ESM-2 650M / 150M / 35M / 3B | 0.606 / 0.641 / 0.605 / 0.582 |
| Probe, AAC-20 / LENGTH / SOURCE | 0.597 / 0.611 / 0.639 |
| Probe, AAC + LENGTH + SOURCE | 0.696 [0.645, 0.822] |
| ESM-2 650M on top of that | +0.005 [−0.039, +0.041]; 150M +0.036 [−0.023, +0.070] |
| Leakage inflation | ESM-2 650M +0.186, AAC-20 +0.129 (extended: +0.138 / +0.068; strict_ge4: +0.176 / +0.035) |
| Extended mode | SOURCE 0.747 > ESM-2 650M 0.671 (N-25) |
| AnOxPePred-only, ESM-2 650M vs AAC+LEN | 0.653 vs 0.603, Δ +0.050 [−0.007, +0.088]; length-matched Δ −0.013 |
| Length-matched LENGTH-only | 0.41 (no residual length signal) |
| Contrastive heads | 0/25 above untrained (Step 6); 13/15 held-out mean cos > 0.95 |

## 5. Figures and tables to include
1. Dataset: label counts, length histogram, source × label table (frontend Step 1 card).
2. Split audit (cross-fold identity by length class) and label × fold.
3. Retrieval AP with CIs for all representations, chance line (Step 5 bar chart).
4. Seeds / scale / reverse-fold bars (Step 6).
5. Collapse: held-out mean cosine per checkpoint (Step 4/5).
6. Probe AUROC with null band, leaky bars (`step5_probe.png`).
7. **Confound figure:** SOURCE / LENGTH / AAC / ESM-2 / combined bars + AnOxPePred-only + length-matched table (`step8_*`).
8. Learning curve (`step8_learning_curve.png`).
9. Split-design table: one split gives 0.593 / 0.602 / 0.655, repeated mean 0.601 (`step8_cv_design.csv`).

## 6. Wording rules (copy these)
* "**no difference detected**", never "equivalent" (no margin was fixed).
* "**no benefit of scale was detected**", never "scale-invariant".
* "AUROC is the fold-mean over 50 test folds (5 folds × 10 fold assignments); confidence intervals are group bootstraps with the fitted models held fixed and are therefore narrower than the true uncertainty."
* "The probe separates MC-active from FRS-only **labels**; the labels are confounded with source and tripeptide share, so the score is not mechanism evidence."
* "GEN means mechanism **not established**, not inactive."
* "Single-split numbers are not reported on their own."
* For the AnOxPePred-only gain: "the gain is not significant and disappears under length matching" — do **not** write "ESM-2 learns length".
* For the loss: "no confirmed-negative peptides are used; collapse is controlled by label-free uniformity and prototype repulsion."
* Name the split "homology-grouped 2-fold split" (not "leave-source-out").

## 7. Limitations (write them yourself before the examiners do)
n = 104 MC-active (75 single-source); 49 retrieval queries; all 18 strict MC-only peptides lie in one fold; tripeptides (36 %) cannot be homology-grouped; labels are assay- and database-level (FRS `source_reported` 631 of 651); no external validation set; one S2 build, one pair rule, one loss; group-bootstrap CIs understate uncertainty; the exploratory approaches were not source-controlled (N-24); extended-mode probe is the most confounded (N-25).

## 8. Methods details you will be asked about
* **Homology groups:** union-find over (identical sequence) ∪ (same CD-HIT 40 % cluster or singleton id) ∪ (normalised edit identity ≥ 70 % with at least one peptide ≥ 4 aa); folds assigned by greedy balance of MC-active count, then size; asserts that no group spans folds.
* **Strict vs extended vs strict_ge4:** per-peptide evidence only (669) / candidate MC evidence included (714) / strict and ≥ 4 aa (410).
* **Retrieval:** queries = MC-active fold-1 peptides; gallery = fold 0; relevant = MC-active; AP, Recall@5/10; exact chance Recall@K = 1 − C(N−R, K)/C(N, K); permutation AP.
* **Probe:** standardise inside the training fold, logistic regression C = 1, balanced weights; whole homology groups per fold, positives balanced greedily; fold code is self-contained (independent of the scikit-learn release).
* **Statistics:** paired bootstrap of ΔAP / ΔAUROC on the same queries or folds; Wilcoxon signed-rank with Holm correction over the comparison family (39).
* **Reproducibility:** every notebook asserts the S2 fingerprint and SHA-256 of inputs; Colab and local replays agree to the third decimal.

## 9. Viva questions and answers (rehearse aloud)
1. **Did your method work?** No. Trained heads are worse than the untrained embedding in 10/10 paired comparisons and 0/25 seeds; I measured it and report it. The contribution is the benchmark and the evaluation that shows why.
2. **Why is this still a contribution?** A leak-controlled benchmark, a measured leakage inflation (+0.13 … +0.19), a confound audit, a reproducible negative result and a documented release contract.
3. **Why did the model collapse?** The alignment term has no denominator; the loss is minimised when all points coincide. Uniformity and prototype repulsion delay it; 13/15 held-out checkpoints still have mean cosine > 0.95.
4. **Is your loss really positive-only?** No confirmed-negative peptides are used, but uniformity and prototype push-away are repulsive terms; I say so (N-18).
5. **Why τ 0.2 and λ 5 instead of the TAF's 0.07 and 0.1?** A sweep that includes the TAF recipe shows it collapses (Step 4 §3); the deviation is documented (E-007).
6. **Why does the probe look better than the model?** It is supervised on the MC/FRS labels, but its AUROC is 0.61 and the single feature `source_group` gets 0.64.
7. **What is the source confound?** Every FRS-only peptide comes from AnOxPePred; 29 of 104 MC-active peptides come from external literature (extended: 54 of 63). A classifier can learn "where did this peptide come from".
8. **What is the length confound?** Mean lengths are equal (5.75 vs 5.86 aa); the difference is the tripeptide share (42.8 % vs 16.3 %). After length matching, LENGTH-only AUROC is 0.41.
9. **Does ESM-2 add anything?** On top of composition + length + source: +0.005 [−0.039, +0.041]; 3B is worse (−0.043). No measurable gain.
10. **Why repeated CV?** One `GroupKFold` split gave 0.593, 0.602 or 0.655 depending on the scikit-learn release; the repeated fold-mean is 0.606 (0.559–0.651 across repeats).
11. **Why fold-mean and not pooled AUROC?** Pooling mixes five fitted intercepts; a single binary feature with exact AUROC 0.639 got 0.55–0.67 pooled.
12. **Is "random noise = 0.38" a bug?** No, it is one low draw (3 sd below its null mean); the null band over 20 seeds is 0.511.
13. **How do you know there is no leakage now?** Union-find homology groups, asserts that no sequence / cluster / group spans folds, a measured leaky control, and a tripeptide limit that I state openly.
14. **What about tripeptides?** 36 % of the set; they cannot be separated into homology-safe folds (one substitution = 67 % identity); this is a stated limit.
15. **What does GEN mean?** Antioxidant by database, mechanism not established — not inactive. Clean negatives are the 27 conflict-free peptides in `AOP-Inactive.csv`.
16. **Why only 49 queries?** The strict MC-active set is small; the CIs reflect it; I do not claim significance for differences smaller than the CI.
17. **Why not tune until it works?** The domain-feature and SupCon trials were pre-registered with a success criterion; both failed it and are reported as negative.
18. **What would you do with more time?** External validation (20–30 new literature peptides), cleaner negatives, repeat retrieval on the AnOxPePred-only subset, assay-level labels.
19. **What should Components 2–4 do with your output?** Use the benchmark and embeddings; do not use the trained heads; do not read probe scores as mechanism evidence (CONTRACT §"must not assume").
20. **Is it reproducible?** Fingerprints and SHA-256 at every step; the release has a MANIFEST and a read-back test; the Step 5 probe is identical on Colab (scikit-learn 1.6.1) and locally (1.9.1).

## 10. PP1 checklist (22–27 Oct 2026)
- [ ] Slides: replace S1-era numbers with §4; add the confound slide (source + tripeptide share) and the "negative result, positive evaluation" message.
- [ ] Remove "positive-only" without the N-18 qualification; remove "9.4 vs 5.8 aa"; remove 0.593 as a standalone number.
- [ ] Show the frontend (`FIXED_V2/FRONTEND/index.html`) as the live demo: Overview → Step 1 confound card → Step 5 probe → Step 8.
- [ ] Rehearse §9 (questions 1, 4, 7, 9, 10 are the most likely).
- [ ] Team: put code under `src/plantaox/c1_procon`, data under `data/*/c1_procon`, tests under `tests/c1_procon`, PR to `dev`.

## 11. Paper plan
Title idea: *"How much mechanism signal is in antioxidant-peptide sequences? A leakage- and confound-controlled benchmark, and the limits of positive-only contrastive learning."* Angle: benchmark + audit + negative result. Venues (realistic): SLIIT/IEEE local conferences; ML-for-biology workshops (MLSB, GEM) that accept negative results; later a bioinformatics journal after an external validation set.
