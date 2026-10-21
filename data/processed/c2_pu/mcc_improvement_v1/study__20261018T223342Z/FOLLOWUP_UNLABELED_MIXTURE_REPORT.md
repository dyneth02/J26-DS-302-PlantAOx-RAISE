# Exploratory unlabeled-mixture follow-up

See FOLLOWUP_AMENDMENT.md for timing and fixed assumptions. No policy was selected using these external results. All rows use fused corrective nnPU, five folds, three seeds, pi=.10 and threshold .5. The same 38 historical controls repeat. Group means are descriptive, not independent validation.

| Training / validation U | Mean MCC ± SD | MCC >0 | Mean AUROC | Mean sensitivity | Mean specificity |
|---|---:|---:|---:|---:|---:|
| C1_train_C1_validation | -0.1977 ± 0.1100 | 0/15 | 0.2876 | 0.6917 | 0.0877 |
| C1C2_train_C1_validation | -0.2174 ± 0.1406 | 0/15 | 0.2828 | 0.6303 | 0.1193 |
| C1C2_train_C1C2_validation | -0.2331 ± 0.1359 | 0/15 | 0.2909 | 0.5220 | 0.1947 |

Native C1/C2 mixture weights and an unmeasured mixture prior do not establish SCAR or true-negative risk. Validation risks across different populations are not directly comparable. Within-policy early stopping uses its own validation risk. Positive-recovery thresholds and all unfavorable results remain in all_evaluations.csv. Paired deltas compare the same outer fold and seed; no independent-run significance test is claimed. C1/C2 near-duplicate families remain an accepted dependence limitation.
