# Threshold investigation

Primary threshold is .5 for every model. No MCC threshold was optimized: C1/C2/C3 have no confirmed negative labels, so assay MCC-optimal threshold is not identifiable. Controls and outer folds are excluded.

Secondary threshold is the empirical lower tenth percentile of positive validation support, frozen in each training summary before external scoring. PN uses E1; PU uses E1+E2. This targets approximately 90% validation recall and does not estimate specificity, calibration or true prevalence. Ties and finite sample quantiles affect achieved recall. Stratified positive bootstrap quantiles (500 replicates, seed2026) describe threshold sampling uncertainty, not source dependence or distribution-shift robustness.

all_evaluations.csv reports BOTH thresholds, including unfavorable results. Do not select the secondary threshold because historical MCC happens to improve. Ranking AUROC is unchanged by threshold choice.
