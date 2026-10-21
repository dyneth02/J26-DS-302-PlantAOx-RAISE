# MCC improvement v1: prospective execution plan

Recorded before new training on 19 October 2026. Branch: experiment/c2-mcc-improvement-v1.

## Evidence and hypotheses

H1: source/domain mismatch dominates ranking failure. Accepted controls score above
positives under all five methods; exclusions and leave-one-control-out checks do
not remove the failure. Compare all 15 descriptors, composition, embedding overlap,
length/descriptor matching and provenance. These are associations, not causes.

H2: high capacity and unstable small-batch PU optimization contribute to saturation.
Use the existing implementations with a bounded regularized recipe: hidden (32,),
Adam lr=0.0003, weight decay=0.001, group batch=256, maximum 50 epochs, patience=8.
This is a compound intervention versus history; feature ablations hold it constant.
Retain direct clamp and corrective beta=0/gamma=1 as distinct algorithms.

H3: feature representation changes generalization. Compare descriptors (15), ESM
(480), fused (495) for all five algorithms, initially outer fold 0 / seed 42.
Use 25 bagging members initially, same number in all new comparisons; accepted
100-member bagging is historical context, not a one-variable comparator.

H4: validation protocol matters. Outer test is GraphPart fold f; validation is
fold (f+1)%5; remaining three folds optimize parameters. No random positive split.
Fit scaler on actual training positives (E1 for PN, E1+E2 for PU), never validation.
Reuse raw cached 495 features; never regenerate frozen features/data. Split C1
deterministically 85/15 with eval seed 42. Exclude all external controls from fitting,
stopping, feature selection, thresholds and priors. C2/C3 remain diagnostic pools.

## Stages and selection

1. Snapshot accepted inventory bytes; reproduce five accepted checkpoints, metrics,
   alignment and probability orientation in a new output directory. Record existing
   freeze-verification failures without repairing historical artifacts.
2. Fold0 pilot: 15 runs (five methods x three representations). Estimate runtime
   before expansion. Neural checkpoints selected by existing validation BCE (PN)
   or nnPU risk at fixed pi=.10 (PU). Sklearn methods retain single-fit semantics.
3. For every outer fold, repeat the representation comparison at seed42. Select
   representation separately inside that fold: minimum validation loss/risk for
   neural methods; maximum validation AP under explicit C1 provisional-zero
   assumption for sklearn methods. Tie-break order descriptors, ESM, fused.
   C1 selection is a surrogate and cannot identify antioxidant specificity.
4. Freeze selections; repeat selected representations with seeds123 and2026 in
   all five folds. Main results: 15 outer-fold/seed runs per method. Pilot candidates
   remain reported; no discard of failures. Seeds do not create independent controls.
5. Fold0 corrective fused prior sensitivity .05/.20 versus .10, plus batch32
   comparator; these are descriptive, never used to pick a prior. A matched
   historical-capacity recipe comparator separates the compound intervention.
6. Only after selection and training finish, evaluate ALL runs on held-out positives
   and the original 38 assay-inactive controls at .5. Report historical fold0
   separately from all-fold retrospective evaluation. Never reverse scores.

## Thresholds, uncertainty, and interpretation

Primary threshold .5. Secondary PU-compatible positive-recovery heuristic: lower
10th percentile of training-derived positive validation scores, frozen before test
evaluation. This targets approximately 90% empirical validation recovery, provides
NO specificity guarantee, and is not MCC optimization. PN uses E1 validation only.
Report its uncertainty with bootstrap quantiles and keep all full-set results.
Stratified peptide bootstrap intervals are descriptive conditional intervals;
publication/family dependence and model-selection uncertainty are not captured.

Main comparisons preserve PN E1-only vs PU E1+E2 distinction. New and historical
training memberships differ due to stricter validation; do not attribute gains to
one parameter. Multi-fold reuse of controls is correlated retrospective evidence.
Seek new assay-matched controls through primary literature, without recycling
AnOxPePred or BIOPEP records as independent observations. No independent claim
without actual acquisition, curation, assay matching and homology screening.

## Compute and preservation

CPU only; torch one thread and bounded BLAS threads. Start 15 fits; extrapolate
from measured cost before full matrix (125 main fits plus sensitivity/comparators).
No paid compute. Durable reports in data/processed/c2_pu/mcc_improvement_v1;
binary runs in data/interim/c2_pu/mcc_improvement_v1. Collision-safe study/run IDs.
Snapshot all accepted inventory entries before/after; never run canonical writing
commands. Full tests that regenerate historical outputs must run in a disposable
workspace copy, not the accepted checkout. No remote push.
