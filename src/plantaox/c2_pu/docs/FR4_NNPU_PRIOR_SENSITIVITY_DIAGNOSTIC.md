# Task 4.3 Post-Acceptance Diagnostic — Positive-Prior Sensitivity and nnPU Negative-Risk Clamping

**Status:** Diagnostic complete. **Does not reopen or change Task 4.3's accepted PASS status** (commit
`c026c3f`) — this is an additional, separately-logged investigation into one reported stability
observation from that accepted run, per `IMPLEMENTATION_STATUS.md`'s own research-limitations note (H).

**Date:** 2026-10-15
**Scope:** GraphPart fold 0 only, E1+E2 labeled positives vs. C1 unlabeled, direct-clamped nnPU variant
only (unchanged from Task 4.3). π ∈ {0.05, 0.10, 0.20}.

---

## A. Purpose

Task 4.3's accepted π=0.10 fold-0 run reported that **≈98–100% of optimizer updates had their
negative-risk term `max(0, R_n)` clamped to zero** in every epoch of training
(`stability_diagnostics.mean_train_clamped_fraction_last_5_epochs ≈ 0.994`,
`fr4_nnpu_baseline_fold0_summary.json`). Under the direct-clamped nnPU objective, a clamped update
contributes **zero gradient** from the unlabeled group — for most updates, training reduces to the
positive-risk term alone, i.e. behavior close to positive-risk-only training rather than the intended
non-negative PU correction.

This document investigates, via a controlled π-sensitivity experiment, **whether this clamping is**:
1. **prior-dependent** (resolved or substantially reduced by choosing a different π within the grid
   Task 4.3 already declared, `PRIOR_SENSITIVITY_GRID = (0.05, 0.10, 0.20)`), or
2. **persistently universal** regardless of π, or
3. **something else** (e.g. an implementation defect, a data/architecture interaction).

This is a **post-acceptance diagnostic**, not a rebuild. The accepted π=0.10 baseline
(`nnpu_risk.py`, `nnpu_baseline.py`, `fr4_nnpu_baseline_fold0_*`) is untouched throughout. The
beta/gamma corrective nnPU training procedure (Kiryo et al. 2017) is **not implemented** here — it is
discussed only as a proposed follow-up (Section H).

---

## B. Experimental controls

Held constant across all three conditions (verified, not assumed, via
`test_c1_train_validation_membership_identical_across_prior_conditions` in
`tests/c2_pu/test_fr4_nnpu_prior_sensitivity_acceptance.py`):

| Control | Value |
|---|---|
| GraphPart fold | 0 |
| Positive pool / challenge pool version | `pp1_baseline_v1` / `pp2_baseline_v1` (frozen, unchanged) |
| Labeled-positive population | E1+E2, same 604 train / 106 validation rows (331 E1 + 273 E2 train, 48 E1 + 58 E2 validation) |
| Unlabeled population | C1, same 3,220 train / 568 validation rows (`pn_baseline.split_c1_train_validation`, `validation_fraction=0.15`, `eval_seed=42`) |
| Feature representation | `fused`, 495-dim (480 ESM-2 + 15 descriptors), fold-0 scaler, unchanged |
| Architecture | `BinaryMlp`, 495 → 128 (ReLU) → 64 (ReLU) → 1 logit |
| Optimizer | Adam, lr=1e-3, weight_decay=1e-4 |
| Batch size | 64 (unlabeled-defines-the-step; E1+E2 cycles via `_CyclingIndexSampler`) |
| `train_seed` / `eval_seed` | 42 / 42 |
| max_epochs / early-stopping patience | 100 / 10 (monitoring validation nnPU risk only) |
| nnPU variant | `direct_clamped` (unchanged — `nnpu_risk.compute_nnpu_risk`, byte-identical) |

**Only π varies**: 0.05, 0.10 (the accepted reference), 0.20.

The π=0.10 condition reuses the accepted Task 4.3 run's own recorded epoch history
(`fr4_nnpu_baseline_fold0_summary.json`) for every risk-trajectory comparison, and its still-present,
SHA-256-verified best checkpoint (`checkpoint_best.pt`, confirmed matching the committed summary's own
recorded hash, read-only, never retrained) for the prediction-distribution comparison. π=0.05 and
π=0.20 are genuine new fold-0 training runs through
`nnpu_prior_diagnostics.train_nnpu_with_diagnostics` — the SAME training loop as the accepted
`nnpu_baseline.train_nnpu_baseline`, with per-update bookkeeping added (verified identical via a
regression test, Section F).

---

## C. Mathematical context — why clamping can suppress unlabeled gradients

```
R_p^+  = E_P[softplus(-f(x))]            (positive-risk component)
R_p^-  = E_P[softplus(f(x))]             (positive-as-negative risk component)
R_u^-  = E_U[softplus(f(x))]             (unlabeled-as-negative risk component)
R_n    = R_u^- - pi * R_p^-              (estimated negative risk)
R_nnPU = pi * R_p^+ + max(0, R_n)        (direct-clamped objective, backpropagated through directly)
```

`max(0, R_n)`'s gradient with respect to any parameter is **exactly zero whenever `R_n < 0`**
(`test_gradient_is_zero_for_unlabeled_group_when_clamped`, `test_nnpu_risk.py`). When `R_n` is
negative for most mini-batches throughout training, the unlabeled group U (C1) contributes no gradient
signal for those updates — the model is effectively trained on `pi * R_p^+` alone, i.e. close to
positive-risk-only optimization, for however large a fraction of updates are clamped. This is a
mathematical property of the direct-clamped objective itself, not a bug — Kiryo et al.'s own paper
introduces the `beta`/`gamma` corrective procedure specifically to address this failure mode by taking
a gradient-**ascent** step on `R_n` below a `-beta` threshold instead of clamping to zero. Task 4.3
explicitly implements only the clamped variant (logged scope decision, `IMPLEMENTATION_STATUS.md`
decision log, 2026-10-15).

`R_n` becomes negative whenever `R_u^-` (the unlabeled group's mean "classified as negative" loss) is
smaller than `pi * R_p^-` (the prior-weighted positive-as-negative loss). Early in training, with the
model near its random initialization, `softplus(f(x)) ≈ softplus(0) = ln(2) ≈ 0.693` for all `x`
regardless of group, so `R_n ≈ (1 - pi) * ln(2) > 0` initially — but as training proceeds and the model
learns to push positive-group logits upward (lowering `R_p^-`) while unlabeled-group logits spread out
(many pushed toward the negative side, lowering `R_u^-` on average since most of C1 is, in fact, not
labeled-positive-like), `R_n` can and typically does cross zero and clamp.

---

## D. Genuine results

All numbers below are read directly from the committed summaries
(`fr4_nnpu_baseline_fold0_summary.json`, `fr4_nnpu_prior_sensitivity_pi0p05_fold0_summary.json`,
`fr4_nnpu_prior_sensitivity_pi0p20_fold0_summary.json`) and the comparison report
(`fr4_nnpu_prior_sensitivity_comparison.json`) — none are estimated or interpolated.

### D.1 Comparison table

| | π=0.05 | π=0.10 (accepted) | π=0.20 |
|---|---|---|---|
| Executed epochs | 39 | 26 | 21 |
| Best epoch | 28 | 15 | 10 |
| Best validation nnPU risk | 8.284e-4 | 1.843e-4 | 1.726e-4 |
| Mean clamped-update fraction (whole run) | 0.9825 | 0.9863 | 0.9915 |
| Final-5-epoch clamped fraction | 0.9960 | 0.9941 | 0.9980 |
| Mean train negative risk (unclamped, epoch-aggregate) | −2.142 | −3.877 | −4.041 |
| Mean validation negative risk (unclamped) | −1.821 | −3.433 | −4.061 |
| Fraction of epochs with negative epoch-aggregate train R_n | 1.0 (39/39) | 1.0 (26/26) | 1.0 (21/21) |
| Fraction of epochs with negative full-validation R_n | 1.0 (39/39) | 1.0 (26/26) | 1.0 (21/21) |
| Validation-side E1 median score (best checkpoint) | 1.000 | 1.000 | 1.000 |
| Validation-side E2 median score (best checkpoint) | 0.9993 | 0.99999 | 0.99999 |
| Validation-side C1 median score (best checkpoint) | 0.00626 | 0.03785 | 0.29765 |
| Validation score saturation (<0.01 / >0.99, combined E1+E2+C1) | 64.7% / 14.1% | 47.5% / 18.4% | 56.8% / 25.1% |

**Do not rank the three priors by raw validation nnPU risk** (Section 9's explicit instruction) — the
objective itself changes with π, so π=0.20's lower raw risk number is not evidence it is "better."

### D.2 Clamping behavior is present from epoch 1, not just late epochs

For the accepted π=0.10 run, the per-epoch `train_clamped_update_fraction` is **0.80 at epoch 0**,
rising to **1.00 by the final epoch** (re-derived directly from
`fr4_nnpu_baseline_fold0_summary.json`'s own `training.history`). Clamping is present from the very
first epoch, not a late-training artifact, and intensifies as training proceeds (consistent with
Section C's account: the model's own learning pushes `R_u^-` down relative to `pi * R_p^-`).

### D.3 Per-update distribution of the unclamped negative risk R_n

`nnpu_prior_diagnostics.py` additionally recorded genuine **per-mini-batch** `R_n` values for the
π=0.05/0.20 runs (the accepted π=0.10 run did not record per-update values — only the epoch aggregate
— so the π=0.10 column below is NOT MEASURED; see Section F for why a retroactive measurement was not
fabricated). At the final executed epoch of each diagnostic run:

| | π=0.05 (epoch 38) | π=0.10 | π=0.20 (epoch 20) |
|---|---|---|---|
| clamped-update fraction, first epoch | 0.6535 | 0.8020 | 0.8713 |
| clamped-update fraction, final epoch | 0.9901 | 1.0000 | 0.9901 |
| per-update R_n min (final epoch) | −7.169 | NOT MEASURED | −12.739 |
| per-update R_n p5 (final epoch) | −6.180 | NOT MEASURED | −11.501 |
| per-update R_n median (final epoch) | −3.994 | NOT MEASURED | −7.445 |
| per-update R_n p95 (final epoch) | −1.958 | NOT MEASURED | −4.038 |
| per-update R_n max (final epoch) | +0.086 | NOT MEASURED | +0.453 |

The per-update `R_n` distribution at the final epoch is clearly concentrated well below zero (median
−3.99 at π=0.05, −7.44 at π=0.20) with a right tail still reaching slightly **positive** values for a
minority of updates (max +0.09 / +0.45) — confirming clamping is a *frequent, not universal* per-update
event even at ≈99% clamped-fraction: a small but real fraction of individual mini-batches still receive
a non-zero negative-risk gradient, consistent with the accepted run's own "98–100%" (not "100%")
framing. The magnitude of the unclamped R_n also scales with π (more negative at π=0.20 than π=0.05),
consistent with `R_n = R_u^- - pi*R_p^-` becoming more negative as the `pi*R_p^-` term shrinks relative
to a growing `pi`-scaled subtraction once the model has learned to separate positives.

### D.4 Best-checkpoint score distributions

Full six-group (train/validation × E1/E2/C1) distributions are recorded in each run's
`best_checkpoint_score_distributions` field and summarized in Plot D
(`fr4_nnpu_prior_sensitivity_plotD_score_distributions.svg`). Labeled positives (E1, E2) are scored
close to 1.0 at every tested π (median ≥0.999 in all three conditions) — i.e. the model clearly
separates labeled positives from the bulk of C1 regardless of π. **C1's own median score rises
materially and monotonically with π** (0.0063 → 0.0378 → 0.2977 for π=0.05/0.10/0.20) — a real,
measured prior-sensitivity in what the model predicts for the unlabeled pool, discussed in Section E.

---

## E. Interpretation

### What the results show

1. **Negative-risk clamping is present at every tested prior and does not resolve within the declared
   sensitivity grid.** Mean clamped-update fractions are 0.982 (π=0.05), 0.986 (π=0.10), 0.992 (π=0.20)
   — a spread of under 1 percentage point across a 4x change in the assumed prior. Lowering π to 0.05
   does **not** materially reduce clamping, and raising π to 0.20 slightly **increases** it (the
   opposite direction from a naive "larger assumed positive fraction → less aggressive negative-risk
   penalty" intuition, though the effect size here is small enough that it should not be over-read).
2. **R_n is negative in every single epoch's aggregate, for every prior tested** (39/39, 26/26, 21/21)
   — the direct-clamped objective's unlabeled-gradient term is suppressed for the large majority of
   training at every π in the declared grid, not merely at the provisional π=0.10 default.
3. **C1 prediction scores ARE prior-sensitive**, even though clamping behavior is not: the model
   assigns C1 a meaningfully higher median score as π increases. This is mathematically expected — a
   larger assumed π means the risk estimator tolerates (and the decision boundary shifts to allow) a
   larger "truly positive" fraction within the unlabeled pool before `R_n` is penalized — but it means
   the π choice has real, visible consequences for downstream predictions even while the
   clamping *mechanism* itself stays persistent.
4. Labeled positives (E1/E2) remain confidently separated from C1's bulk at every π — no complete
   collapse to all-positive or all-negative predictions was observed in any condition
   (`diverging_risk_detected: false` in all three; validation saturation fractions are substantial but
   not total in any condition).

### What the results do NOT establish

- They do **not** establish that the direct-clamped nnPU implementation contains a defect. The
  persistent clamping is consistent with the known, documented mathematical behavior of the
  direct-clamped objective (Section C) interacting with this specific positive/C1 feature-distribution
  pair (Task 2.5's own KS-test findings already established FR1-positives and C1 are drawn from
  measurably different distributions on every tested descriptor) — not necessarily an implementation
  error. Distinguishing "expected consequence of the clamped-objective-plus-distribution-mismatch" from
  "an actual implementation defect" would require comparing against the beta/gamma corrective variant
  (Section H) or an independent reference implementation, neither of which was done here.
- They do **not** establish which π is "biologically correct." None of the three values is a measured
  biological prevalence (`PRIOR_PROVENANCE_NOTE`, unchanged from Task 4.3); the sensitivity run shows
  how model behavior responds to the assumption, not which assumption is true.
- The five-fold GraphPart split was not exercised — this is fold-0-only, matching Task 4.3's own scope.
- Per-update R_n percentiles are only available for π=0.05/0.20 (new instrumentation), not retroactively
  for the accepted π=0.10 run — see Section F.

### Diagnostic questions (Section 7 of the task brief), answered from the data above

1. **Does lowering π to 0.05 reduce clamping?** Marginally (0.986 → 0.982 mean fraction) — not a
   material reduction.
2. **Does increasing π to 0.20 increase clamping?** Marginally (0.986 → 0.992) — small effect, same
   direction as a naive expectation but not large.
3. **Does R_n remain positive for any substantial portion of training?** At the epoch-aggregate level,
   no — R_n's aggregate is negative in literally every epoch of every condition. At the per-update
   level (π=0.05/0.20 only), a visible minority of individual mini-batches do see positive R_n (Section
   D.3), so the unlabeled gradient is not *literally* zero 100% of the time, consistent with the
   accepted run's own "98–100%" framing (not "100%").
4. **Is clamping present from epoch 1 or only later?** Present from epoch 1 (≈80% at the first epoch of
   the π=0.10 run), intensifying toward ≈100% by the final epochs in all three conditions.
5. **Are full-validation R_n values consistent with per-mini-batch behavior?** Qualitatively yes — the
   full-validation R_n is negative in every epoch of every condition, consistent with the
   epoch-aggregate training-side R_n also being negative in every epoch; both point the same direction.
6. **Do C1 prediction scores meaningfully change with π?** Yes, materially (Section D.4) — this is the
   clearest prior-sensitive signal found in this investigation.
7. **Does the model show all-positive/all-negative collapse?** No — `diverging_risk_detected: false` in
   all three conditions, and validation score distributions retain real spread (not 100% saturated at
   either extreme) in every condition.
8. **Is the behavior consistent with the direct-clamped rule?** Yes — the gradient-is-zero-when-clamped
   property is a verified unit-test invariant of the estimator itself (`test_nnpu_risk.py`), and the
   observed training dynamics (persistent negative aggregate R_n, near-ceiling clamped fractions) are
   the direct, expected consequence of that rule given this prior range and feature distribution.
9. **Is there evidence of an implementation defect, or is this expected given the objective/data/prior
   combination?** No defect evidence was found in this investigation. The pattern is consistent with
   the documented mathematical behavior of the direct-clamped objective combined with the already-known
   FR1-positive-vs-C1 distributional mismatch (Task 2.5). This is not a proof of absence of a defect —
   only that nothing in this diagnostic's scope (risk-component math, per-update clamping counts,
   score distributions) points to one.
10. **What scientific limitations remain unresolved?** Whether the beta/gamma corrective procedure
    would materially change this picture is unknown (not implemented/tested here — Section H). Whether
    a π outside {0.05, 0.10, 0.20} would behave differently is unknown. Five-fold validation was not
    performed. The C1-vs-positive distributional mismatch itself (Task 2.5) remains unresolved and is
    outside this diagnostic's scope.

---

## F. Implementation integrity

- **Accepted baseline preserved, verified by SHA-256 before and after every diagnostic run in this
  session:**
  - `fr4_nnpu_baseline_fold0_summary.json`: unchanged.
  - `fr4_nnpu_baseline_fold0_learning_curve.svg`: unchanged.
  - Accepted best/last checkpoint weights (`checkpoint_best.pt`/`checkpoint_last.pt` under
    `data/interim/c2_pu/fr4_nnpu_baseline_runs/fr4_nnpu_baseline_fold0__20261014T183214Z/`, gitignored
    but present on disk in this checkout): re-hashed and confirmed to match the SHA-256 the committed
    summary itself recorded, both before this diagnostic's work began and after every π=0.05/0.20
    training run — see `test_accepted_baseline_summary_and_learning_curve_are_byte_identical_after_diagnostics`
    and `test_accepted_baseline_best_checkpoint_weights_are_unchanged_after_diagnostics`.
  - Frozen `pp1_baseline_v1`/`pp2_baseline_v1` manifests, FR3 feature-cache manifest/fusion
    scalers/record map, and `c3_similarity_ranking.csv`: confirmed byte-unchanged.
  - Task 4.2 PN baseline outputs (`fr4_pn_baseline_fold0_summary.json`): confirmed byte-unchanged.
- **No changes were made to `nnpu_risk.py` or `nnpu_baseline.py`.** All new diagnostic code lives in
  two new modules (`nnpu_prior_diagnostics.py`, `nnpu_prior_sensitivity_report.py`) that import and
  reuse the accepted risk estimator and `_CyclingIndexSampler` unchanged.
- **Regression guard:** `test_diagnostic_loop_reproduces_accepted_loops_epoch_aggregates_at_same_prior`
  runs the diagnostic training loop (`train_nnpu_with_diagnostics`) and the accepted loop
  (`train_nnpu_baseline`) side-by-side at the same prior (π=0.10), same seeds, same reduced epoch count,
  and asserts every pre-existing epoch-level metric field is identical between the two — confirming the
  new per-update instrumentation adds bookkeeping only and does not change what is actually trained.
- **Separate output paths.** Every diagnostic artifact (run directories, committed summaries, learning
  curves, plots, provenance log) uses a `fr4_nnpu_prior_sensitivity_*` naming/path convention, entirely
  distinct from `fr4_nnpu_baseline_*` — structurally unable to collide with or overwrite the accepted
  baseline's files (enforced by distinct path templates in `run.py`, not by convention alone).
- **Why per-update π=0.10 percentiles are NOT MEASURED, not fabricated:** the accepted π=0.10 run (Task
  4.3, 2026-10-14) only recorded batch-size-weighted epoch aggregates, not raw per-update values (that
  instrumentation did not exist yet). Rather than inventing plausible-looking percentiles, this report
  states the limitation explicitly (Section D.3) wherever it applies.
- **Test results:**
  - New diagnostic-utility unit tests: `tests/c2_pu/test_nnpu_prior_diagnostics.py` (18 tests) +
    `tests/c2_pu/test_nnpu_prior_sensitivity_report.py` (13 tests) — torch-free, always run, zero
    gating.
  - New acceptance tests: `tests/c2_pu/test_fr4_nnpu_prior_sensitivity_acceptance.py` (14 tests,
    gated to skip when FR3 outputs/accepted baseline aren't present locally) — real reduced-epoch smoke
    runs, reproducibility, controlled-variable (identical C1/positive membership across priors)
    verification, the regression guard above, and full baseline-preservation checks.
  - Full repository suite: `PYTHONPATH=src ./.venv/Scripts/python.exe -m pytest tests/ -q`
    → **576 passed, 1 skipped, 0 failed** (1171.16s / 19m31s). Pre-diagnostic reference (Task 4.3
    acceptance): 531 passed, 1 skipped. New tests added by this diagnostic: 45 (18 + 13 + 14). The
    single skip is the pre-existing, unchanged `test_embeddings.py` torch-in-WSL skip, not introduced
    by this work. Running this suite re-executes the accepted Task 4.2/4.3 baselines' own acceptance
    tests (a pre-existing behavior of those test files, unrelated to this diagnostic) and the FR1-FR3
    provenance-log-append side effects of live stage reruns; both were confirmed to change only
    timestamp/run-directory/provenance-log fields (re-verified byte-identical on every field that
    matters: training history, best epoch, checkpoint weights) and were restored to their
    pre-session committed state via `git checkout --` before this diagnostic's own artifacts were
    finalized, so the final diff contains only this diagnostic's own new files.

---

## G. Scientific conclusion

**Classification: Persistently clamped.**

Negative-risk clamping under the direct-clamped nnPU objective is present at every tested prior
(π ∈ {0.05, 0.10, 0.20}), with mean per-update clamped fractions all in a narrow 0.982–0.992 band and
the epoch-aggregate negative risk negative in literally every epoch of every condition tested. This is
**not** resolved by retuning π within the declared sensitivity grid. It is accompanied by a secondary,
genuinely prior-**sensitive** finding — C1's median predicted score shifts materially with π — so the
overall picture is not "nothing about this model depends on π," but the specific stability concern Task
4.3 raised (clamping suppressing the unlabeled-group gradient) is prior-insensitive within this grid.

This finding is reported as a meaningful negative result, not a defect claim and not a reason to
retune the architecture, dataset, or model-selection criterion (per the task brief's explicit
instruction not to chase a more favorable-looking result by repeated reruns — these are the first and
only π=0.05/0.20 training runs performed for this diagnostic).

---

## H. Recommendation

1. **Proceeding to Task 4.4 (Two-Step PU, PU-Bagging) is reasonable.** This diagnostic did not find
   evidence that the direct-clamped nnPU estimator is broken — only that, as implemented and under this
   prior range, it behaves close to positive-risk-only training for most updates, a documented and now
   quantified limitation rather than a blocking defect. Two-Step PU and PU-Bagging do not depend on the
   nnPU risk estimator and are unaffected by this finding.
2. **A separately-scoped comparison between Variant A (the accepted direct-clamped nnPU) and Variant B
   (the original Kiryo et al. beta/gamma corrective nnPU training procedure) is advisable before relying
   on nnPU results in Task 4.5's cross-baseline evaluation or Task 4.6's curriculum**, specifically to
   determine whether the corrective procedure materially changes the unlabeled-gradient-suppression
   behavior documented here. This is a proposed follow-up only — **not implemented in this session**,
   per the task brief's explicit instruction.
3. Do not treat the lower raw nnPU validation risk at π=0.20 (1.726e-4) as evidence that π=0.20 is the
   "right" prior — the objective itself changes with π, and this diagnostic found no basis for
   preferring one value over another on biological grounds.
