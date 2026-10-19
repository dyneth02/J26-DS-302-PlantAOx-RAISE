# Results summary (generated from results/*.csv)

Primary mode `strict`; train fold 0 → evaluate fold 1; MC-active queries; chance AP 0.177, chance Recall@5 0.591.

## MC retrieval (Step 5)
| representation | kind | n_queries | AP | AP_lo | AP_hi | lift | R@5 | mean_cos_heldout |
|---|---|---|---|---|---|---|---|---|
| LENGTH | baseline | 49 | 0.223 | 0.209 | 0.238 | 1.261 | 0.714 | nan |
| RAW 650M | baseline | 49 | 0.202 | 0.192 | 0.211 | 1.140 | 0.653 | nan |
| AAC-20 | baseline | 49 | 0.200 | 0.191 | 0.211 | 1.132 | 0.755 | nan |
| ARI-Checkpoint-Floored | model | 49 | 0.192 | 0.184 | 0.201 | 1.084 | 0.816 | 0.988 |
| RAW 150M | baseline | 49 | 0.186 | 0.178 | 0.195 | 1.052 | 0.735 | nan |
| DESC-14 | baseline | 49 | 0.186 | 0.171 | 0.203 | 1.051 | 0.531 | nan |
| k-NN+ARI-Checkpoint | model | 49 | 0.185 | 0.175 | 0.197 | 1.047 | 0.735 | 0.992 |
| RANDOM (chance) | chance | 49 | 0.177 | nan | nan | 1.000 | 0.591 | nan |
| Primary-MechEqual | model | 49 | 0.176 | 0.167 | 0.186 | 0.995 | 0.776 | 0.953 |
| MechEqual-MaxSpread | model | 49 | 0.173 | 0.152 | 0.201 | 0.979 | 0.327 | 0.182 |
| k-NN-150M | model | 49 | 0.168 | 0.160 | 0.176 | 0.948 | 0.531 | 0.978 |
| Primary-MaxSpread | model | 49 | 0.164 | 0.155 | 0.175 | 0.927 | 0.490 | 0.369 |
| k-NN-Pairing | model | 49 | 0.160 | 0.152 | 0.169 | 0.903 | 0.490 | 0.986 |
| Primary-150M | model | 49 | 0.154 | 0.146 | 0.163 | 0.869 | 0.633 | 0.995 |
| HP2-Fusion | model | 49 | 0.153 | 0.144 | 0.164 | 0.866 | 0.571 | 0.991 |
| HP1-Random | model | 49 | 0.144 | 0.128 | 0.164 | 0.814 | 0.408 | 0.999 |
| ARI-Checkpoint-Only | model | 49 | 0.143 | 0.137 | 0.150 | 0.810 | 0.673 | 0.998 |
| Primary-Balanced | model | 49 | 0.142 | 0.136 | 0.149 | 0.802 | 0.449 | 0.997 |
| Primary | model | 49 | 0.140 | 0.135 | 0.147 | 0.793 | 0.551 | 0.997 |

## Paired comparisons (Step 5, Holm-corrected)
| comparison | mode | n | delta_AP | ci_lo | ci_hi | p_holm | verdict |
|---|---|---|---|---|---|---|---|
| Primary vs untrained ESM-2 650M | strict | 49 | -0.061 | -0.071 | -0.052 | 0.000 | RAW 650M better |
| Primary vs amino-acid composition | strict | 49 | -0.060 | -0.070 | -0.051 | 0.000 | AAC-20 better |
| Primary vs length only | strict | 49 | -0.083 | -0.099 | -0.068 | 0.000 | LENGTH better |
| Primary-MaxSpread vs untrained ESM-2 650M | strict | 49 | -0.038 | -0.050 | -0.025 | 0.000 | RAW 650M better |
| Primary-MaxSpread vs amino-acid composition | strict | 49 | -0.036 | -0.049 | -0.024 | 0.000 | AAC-20 better |
| Primary-MaxSpread vs length only | strict | 49 | -0.059 | -0.076 | -0.042 | 0.000 | LENGTH better |
| Primary-MechEqual vs untrained ESM-2 650M | strict | 49 | -0.026 | -0.034 | -0.017 | 0.000 | RAW 650M better |
| Primary-MechEqual vs amino-acid composition | strict | 49 | -0.024 | -0.038 | -0.011 | 0.013 | AAC-20 better |
| Primary-MechEqual vs length only | strict | 49 | -0.047 | -0.063 | -0.031 | 0.000 | LENGTH better |
| MechEqual-MaxSpread vs untrained ESM-2 650M | strict | 49 | -0.028 | -0.048 | -0.006 | 0.005 | RAW 650M better |
| MechEqual-MaxSpread vs amino-acid composition | strict | 49 | -0.027 | -0.048 | -0.003 | 0.009 | AAC-20 better |
| MechEqual-MaxSpread vs length only | strict | 49 | -0.050 | -0.076 | -0.021 | 0.000 | LENGTH better |
| k-NN-Pairing vs untrained ESM-2 650M | strict | 49 | -0.042 | -0.049 | -0.034 | 0.000 | RAW 650M better |
| k-NN-Pairing vs amino-acid composition | strict | 49 | -0.041 | -0.051 | -0.030 | 0.000 | AAC-20 better |
| k-NN-Pairing vs length only | strict | 49 | -0.063 | -0.079 | -0.048 | 0.000 | LENGTH better |
| Primary-Balanced vs untrained ESM-2 650M | strict | 49 | -0.060 | -0.069 | -0.051 | 0.000 | RAW 650M better |
| Primary-Balanced vs amino-acid composition | strict | 49 | -0.058 | -0.068 | -0.050 | 0.000 | AAC-20 better |
| Primary-Balanced vs length only | strict | 49 | -0.081 | -0.097 | -0.066 | 0.000 | LENGTH better |
| HP2-Fusion vs untrained ESM-2 650M | strict | 49 | -0.048 | -0.060 | -0.037 | 0.000 | RAW 650M better |
| HP2-Fusion vs amino-acid composition | strict | 49 | -0.047 | -0.058 | -0.036 | 0.000 | AAC-20 better |
| HP2-Fusion vs length only | strict | 49 | -0.070 | -0.088 | -0.051 | 0.000 | LENGTH better |
| Primary-150M vs untrained ESM-2 150M | strict | 49 | -0.032 | -0.041 | -0.023 | 0.000 | RAW 150M better |
| untrained ESM-2 650M vs amino-acid composition | strict | 49 | 0.001 | -0.007 | 0.010 | 1.000 | no difference detected |
| untrained ESM-2 650M vs length only | strict | 49 | -0.022 | -0.038 | -0.006 | 0.089 | LENGTH better |
| amino-acid composition vs length only | strict | 49 | -0.023 | -0.041 | -0.005 | 0.221 | LENGTH better |
| HP1: real pairs vs random pairs (Primary vs HP1-Random) | strict | 49 | -0.004 | -0.025 | 0.014 | 0.696 | no difference detected |
| selection rule: lowest loss vs most spread (Primary vs MaxSpread) | strict | 49 | -0.024 | -0.032 | -0.016 | 0.000 | Primary-MaxSpread better |
| MC resampling: Primary vs Balanced | strict | 49 | -0.002 | -0.004 | 0.001 | 0.696 | no difference detected |
| MC equal steps: Primary vs MechEqual | strict | 49 | -0.036 | -0.047 | -0.026 | 0.000 | Primary-MechEqual better |
| backbone: 150M vs 650M (percentile pairs) | strict | 49 | 0.013 | 0.007 | 0.021 | 0.002 | Primary-150M better |
| pairing: k-NN vs percentile (650M) | strict | 49 | 0.019 | 0.012 | 0.029 | 0.000 | k-NN-Pairing better |
| backbone: 150M vs 650M (k-NN pairs) | strict | 49 | 0.008 | 0.003 | 0.012 | 0.015 | k-NN-150M better |
| HP2: fusion vs ESM-2 only | strict | 49 | 0.013 | 0.006 | 0.020 | 0.026 | HP2-Fusion better |
| Primary-Extended vs untrained ESM-2 650M (mode extended) | extended | 75 | -0.068 | -0.084 | -0.050 | 0.000 | RAW 650M better |
| Primary-Extended vs amino-acid composition (mode extended) | extended | 75 | -0.066 | -0.080 | -0.049 | 0.000 | AAC-20 better |
| untrained ESM-2 650M vs composition (mode extended) | extended | 75 | 0.003 | -0.005 | 0.011 | 1.000 | no difference detected |
| Primary-StrictGE4 vs untrained ESM-2 650M (mode strict_ge4) | strict_ge4 | 42 | -0.052 | -0.063 | -0.041 | 0.000 | RAW 650M better |
| Primary-StrictGE4 vs amino-acid composition (mode strict_ge4) | strict_ge4 | 42 | -0.062 | -0.075 | -0.047 | 0.000 | AAC-20 better |
| untrained ESM-2 650M vs composition (mode strict_ge4) | strict_ge4 | 42 | -0.009 | -0.020 | -0.000 | 0.696 | AAC-20 better |

## Supervised probe, repeated grouped CV vs leaky folds (Step 5 v4; fold-mean AUROC)
| mode | features | n | AUROC | lo | hi | AUROC_rep_min | AUROC_rep_max | cv |
|---|---|---|---|---|---|---|---|---|
| strict | ESM-2 35M | 669 | 0.605 | 0.552 | 0.705 | 0.582 | 0.624 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | ESM-2 150M | 669 | 0.641 | 0.597 | 0.740 | 0.583 | 0.691 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | ESM-2 650M | 669 | 0.606 | 0.559 | 0.724 | 0.559 | 0.651 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | ESM-2 3B | 669 | 0.582 | 0.537 | 0.686 | 0.528 | 0.612 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | AAC-20 | 669 | 0.597 | 0.550 | 0.713 | 0.555 | 0.619 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | DESC-14 | 669 | 0.517 | 0.463 | 0.651 | 0.497 | 0.537 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | LENGTH | 669 | 0.611 | 0.557 | 0.669 | 0.602 | 0.622 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | AAC-20 + LENGTH | 669 | 0.609 | 0.560 | 0.715 | 0.560 | 0.630 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | SOURCE | 669 | 0.639 | 0.598 | 0.713 | 0.639 | 0.640 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | AAC-20 + LENGTH + SOURCE | 669 | 0.696 | 0.645 | 0.822 | 0.672 | 0.720 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | ESM-2 650M + AAC-20 + LENGTH + SOURCE | 669 | 0.701 | 0.660 | 0.815 | 0.648 | 0.735 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | ESM-2 150M + AAC-20 + LENGTH + SOURCE | 669 | 0.731 | 0.688 | 0.829 | 0.694 | 0.779 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | RANDOM noise (seed 0) | 669 | 0.376 | 0.339 | 0.435 | 0.345 | 0.408 | repeated grouped CV (5 folds x 10, homology_group) |
| strict | NULL band: RANDOM noise 64-d, 20 seeds | 669 | 0.511 | 0.430 | 0.567 | nan | nan | repeated grouped CV (5 folds x 10, homology_group) |
| strict | ESM-2 650M | 669 | 0.792 | 0.711 | 0.850 | 0.765 | 0.812 | LEAKY stratified random folds (5 folds x 10) |
| strict | AAC-20 | 669 | 0.727 | 0.642 | 0.790 | 0.712 | 0.740 | LEAKY stratified random folds (5 folds x 10) |
| extended | ESM-2 35M | 714 | 0.697 | 0.651 | 0.788 | 0.679 | 0.723 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | ESM-2 150M | 714 | 0.695 | 0.651 | 0.771 | 0.673 | 0.715 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | ESM-2 650M | 714 | 0.671 | 0.621 | 0.762 | 0.656 | 0.714 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | ESM-2 3B | 714 | 0.672 | 0.628 | 0.757 | 0.650 | 0.690 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | AAC-20 | 714 | 0.683 | 0.636 | 0.776 | 0.658 | 0.698 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | DESC-14 | 714 | 0.627 | 0.580 | 0.713 | 0.599 | 0.651 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | LENGTH | 714 | 0.665 | 0.624 | 0.730 | 0.649 | 0.676 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | AAC-20 + LENGTH | 714 | 0.704 | 0.660 | 0.784 | 0.669 | 0.723 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | SOURCE | 714 | 0.747 | 0.704 | 0.818 | 0.747 | 0.748 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | AAC-20 + LENGTH + SOURCE | 714 | 0.798 | 0.751 | 0.896 | 0.778 | 0.824 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | ESM-2 650M + AAC-20 + LENGTH + SOURCE | 714 | 0.790 | 0.751 | 0.877 | 0.772 | 0.828 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | ESM-2 150M + AAC-20 + LENGTH + SOURCE | 714 | 0.822 | 0.784 | 0.897 | 0.805 | 0.849 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | RANDOM noise (seed 0) | 714 | 0.465 | 0.426 | 0.516 | 0.436 | 0.501 | repeated grouped CV (5 folds x 10, homology_group) |
| extended | NULL band: RANDOM noise 64-d, 20 seeds | 714 | 0.501 | 0.455 | 0.555 | nan | nan | repeated grouped CV (5 folds x 10, homology_group) |
| extended | ESM-2 650M | 714 | 0.808 | 0.762 | 0.843 | 0.794 | 0.815 | LEAKY stratified random folds (5 folds x 10) |
| extended | AAC-20 | 714 | 0.751 | 0.704 | 0.792 | 0.741 | 0.758 | LEAKY stratified random folds (5 folds x 10) |
| strict_ge4 | ESM-2 35M | 410 | 0.651 | 0.593 | 0.708 | 0.606 | 0.684 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | ESM-2 150M | 410 | 0.632 | 0.576 | 0.731 | 0.610 | 0.679 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | ESM-2 650M | 410 | 0.600 | 0.544 | 0.700 | 0.563 | 0.635 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | ESM-2 3B | 410 | 0.612 | 0.557 | 0.686 | 0.549 | 0.640 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | AAC-20 | 410 | 0.683 | 0.586 | 0.738 | 0.639 | 0.730 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | DESC-14 | 410 | 0.596 | 0.518 | 0.654 | 0.534 | 0.650 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | LENGTH | 410 | 0.599 | 0.491 | 0.656 | 0.593 | 0.605 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | AAC-20 + LENGTH | 410 | 0.677 | 0.580 | 0.732 | 0.635 | 0.718 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | SOURCE | 410 | 0.632 | 0.581 | 0.712 | 0.631 | 0.633 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | AAC-20 + LENGTH + SOURCE | 410 | 0.689 | 0.617 | 0.786 | 0.632 | 0.745 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | ESM-2 650M + AAC-20 + LENGTH + SOURCE | 410 | 0.668 | 0.617 | 0.761 | 0.634 | 0.703 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | ESM-2 150M + AAC-20 + LENGTH + SOURCE | 410 | 0.705 | 0.648 | 0.800 | 0.681 | 0.737 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | RANDOM noise (seed 0) | 410 | 0.531 | 0.476 | 0.593 | 0.511 | 0.570 | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | NULL band: RANDOM noise 64-d, 20 seeds | 410 | 0.486 | 0.423 | 0.544 | nan | nan | repeated grouped CV (5 folds x 10, homology_group) |
| strict_ge4 | ESM-2 650M | 410 | 0.776 | 0.691 | 0.838 | 0.731 | 0.818 | LEAKY stratified random folds (5 folds x 10) |
| strict_ge4 | AAC-20 | 410 | 0.718 | 0.615 | 0.804 | 0.693 | 0.741 | LEAKY stratified random folds (5 folds x 10) |

## Seed spread (Step 6)
_(not run: `step6_seed_spread.csv` not found — run Step 6)_

## Scale sweep (Step 6)
_(not run: `step6_scale_sweep.csv` not found — run Step 6)_

## Reverse fold direction (Step 6)
_(not run: `step6_reverse.csv` not found — run Step 6)_
