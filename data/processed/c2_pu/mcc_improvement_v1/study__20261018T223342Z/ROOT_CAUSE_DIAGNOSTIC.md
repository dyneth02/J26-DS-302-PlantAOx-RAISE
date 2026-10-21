# Root-cause diagnostic

Five accepted checkpoints reproduce MCC, AUROC, AP and recall to 1e-12. Labels are positive=1/control=0; sigmoid and sklearn column1 point toward positive support. All feature IDs and pool memberships align; source duplicate C1 IDs agree in sequence, pool, tier and fold. Existing loader checks ID/sequence disjointness. No blocking prediction bug was found.

Evidence ranking:

1. **Strong descriptive evidence:** broad historical ranking failure and source/descriptor shift. See descriptor_shift_statistics.csv (all 15 descriptors; BH-adjusted exploratory tests), composition, train-fitted PCA and nearest-training distances. Source, sequence family and assay effects remain confounded; shifts do not prove shortcut causation.
2. **Strong optimization evidence:** accepted direct clamping suppresses U gradients in ~99% of updates and saturates scores. Corrective gradients are meaningful but do not by themselves establish assay discrimination. New comparisons retain both variants and report their branches.
3. **Confirmed protocol limitation:** historical scaling includes 106 inner-validation positives; outer test remains isolated. New scaling uses only actual optimization positives and inner validation is a separate GraphPart fold. This need not explain the direction of historical failure.
4. **Plausible, unresolved:** C1-only validation and unmeasured prior/SCAR assumptions poorly represent assay-specific activity. Prior sensitivity cannot estimate real prevalence.
5. **Insufficient causal support:** particular assay mechanisms, sources or peptide families cause the failure. DOI-level controls lack harmonized conditions; two conflicting annotations do not explain the full negative result. No labels are changed.

Threshold optimization against controls is prohibited; AUROC below .5 is a ranking issue. Length/descriptor matching is diagnostic only and always accompanies the full original set. No fresh assay-matched independent dataset has been curated.
