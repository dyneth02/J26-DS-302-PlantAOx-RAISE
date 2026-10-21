# Exploratory follow-up: unlabeled distribution and validation policy

Declared after the main 129 fits and initial retrospective metrics were available.
This timing is explicit: these follow-ups cannot be presented as an untouched
confirmatory experiment. No external metric determines a hyperparameter, prior,
threshold, checkpoint or winner in this follow-up.

Rationale: the diagnostic nearest-training-positive ESM distance is ~22.8 for C1
and ~18.3 for C2, versus ~14.5 for held-out positives and ~15.6 for controls.
Accepted curriculum already raised C1-only validation as a limitation. A broader
unlabeled distribution is therefore a targeted remaining hypothesis, not an
unbounded search. Distance alone does not prove a better PU sampling model.

Fixed configuration: corrective nnPU, fused features, hidden(32,), lr=.0003,
weight_decay=.001, batch256, max50 epochs, patience8, pi=.10, beta0/gamma1.
Train on C1-training + C2-training (native counts, not equal source resampling).
Split C2 deterministically 85/15 with seed42, independent of C1 and positive folds.
Neither C3 nor assay controls enter any fit or criterion. Training-positive-only
scaling and GraphPart outer/inner boundaries remain unchanged.

Two validation policies are reported side by side, without choosing a winner:

1. Preserve C1-only unlabeled validation.
2. Use C1-validation + C2-validation in native proportions.

Both use the existing nnPU risk under the same provisional pi. Risk values across
these different validation populations are **not** directly comparable. For each
policy, checkpoint selection is solely its own validation risk. Positive q10
thresholds remain validation-positive-only. Run all 5 folds x 3 seeds for both
policies (30 fits) because observed fitting cost is seconds per run on local CPU.

Also repeat C1-only fused seeds123/2026 in fold3, where the main study selected
ESM, to provide a complete matched 15-run C1-only fused comparator. These two
fits are not new hyperparameter candidates. Existing C1-only fused runs supply
the remaining 13 matched comparisons.

Scientific assumptions: C1 and C2 are unlabeled, not inactive. The mixture prior
.10 is unmeasured and may be inappropriate for either source. E1/E2 labeled
positives may not represent the mixture's hidden positives (SCAR/mixture shift).
Including C2 changes both sampling and possible contamination, and known accepted
C1/C2 near-duplicate families remain a dependence limitation. Native count weights
define the mixture; no assay-supported negative risk becomes identifiable.

Report all outcomes, including negative MCC and whether specificity is obtained
merely by sacrificing positive recall. Do not overwrite main selection decisions.
