# Component 4 Methodology and Definitions

This page documents the research design, not completed calculations. The formulas below require implementation, tests, and the validation evidence in [SCREEN_PP1_VALIDATION.md](SCREEN_PP1_Validation) before they can support reported findings.

## Candidate generation (FR1)

The target inputs are UniProt Swiss-Prot reviewed proteins for four plants: *Glycine max* (soybean), *Oryza sativa* subsp. *japonica* (rice), *Brassica napus* (rapeseed), and *Olea europaea* (olive; taxonomy 4146). The inventory specifies dropping proteins shorter than 50 residues and sequences with non-standard residues, while logging exclusions.

The intended protocol applies pepsin first and trypsin to the resulting pepsin fragments. Retain fragments of 3–20 amino acids, comprising at least two distinct amino-acid types from the standard 20-letter alphabet. Preserve every parent accession, source plant, fragment coordinates, and digestion path when duplicate sequences are merged.

### Digestion implementation deviation

The proposal and plain-language explainer name BIOPEP-UWM. The PP1 inventory instead directs a Python rule-based implementation if no usable public batch interface is available, with pepsin pH 1.3 as the nearest available rule to the proposal's pH 1.2. This is a documented deviation, not an equivalence claim. Record enzyme rule provenance, missed-cleavage policy, and a BIOPEP-UWM spot-check if available. The implementation is not yet present, so actual cleavage behavior is not established.

### Deduplication

The PP1 plan makes exact-sequence deduplication canonical and requires retaining all parent provenance. CD-HIT 90% identity is optional for 10–20 AA peptides only, because very short sequences have severe word-size/minimum-length constraints. The plain-language overview's blanket CD-HIT description is not the PP1 acceptance rule. Any clustered output must retain representative-to-member mapping and exact tool parameters.

## ESM-2 representations

The target model is `esm2_t33_650M_UR50D`, producing 1280-dimensional representations. The project inventory proposes layer 33, mean pooling over residue positions excluding BOS/EOS, and fp16 storage. The proposal also requires consistency with C1. Before implementation, record the agreed layer, tokenization, pooling, dtype, model weight identifier/checksum, software version, and whether embeddings are normalized before cosine operations. A `.npy` matrix without a row-ID map and manifest is not a valid embedding artifact.

## Applicability domain (FR2)

For embedding vector \(x\) and reference centroid \(c\), cosine distance is:

\[
d_{AD}(x) = 1 - \frac{x \cdot c}{\|x\|\,\|c\|}.
\]

The candidate centroid and calibration distribution must be fitted on the versioned AOP reference cloud only, then frozen. The inventory recommends defining \(\mu_{cloud}\) and \(\sigma_{cloud}\) using cloud-member distances to the centroid with leave-one-out treatment, to avoid evaluating each reference sequence against a centroid containing itself. The exact calculation, population/sample standard deviation convention, and treatment of small clouds require a logged decision.

Proposed default tiers are:

| Tier | Proposed rule | Interpretation |
|---|---|---|
| Tier 1 | \(d_{AD} < \mu_{cloud}+\sigma_{cloud}\) | Within the tighter reference-distance region |
| Tier 2 | \(\mu_{cloud}+\sigma_{cloud} \le d_{AD} < \mu_{cloud}+2\sigma_{cloud}\) | Uncertain / expanded domain |
| Tier 3 | \(d_{AD} \ge \mu_{cloud}+2\sigma_{cloud}\) | Out-of-domain; abstain from positive ranking |

Threshold sensitivity at multipliers 1.0, 1.5, and 2.0 is proposed. Tier distributions and distance histograms must be reported by plant; degenerate distributions trigger diagnostics, not threshold tuning to improve appearances.

## Combined score (FR4)

The proposal defines the weighted score in terms of a normalized AD distance:

\[
CS = w_1\,SIM_{C1} + (1-w_1)\,PROB_{C2}\,(1-d_{norm}),
\qquad CS=0\;\text{for Tier 3}.
\]

The default is \(w_1=0.5\). The PP1 inventory proposes \(d_{norm}=\min(d_{AD}/(\mu_{cloud}+2\sigma_{cloud}),1)\); the proposal text is inconsistent about whether `d_AD` is already normalized. This normalization must be frozen in the decision log and applied consistently before any score is produced. Planned weight sensitivity is \(w_1\in\{0.25,0.5,0.75\}\).

The score is a retrieval ranking function, not a calibrated probability of antioxidant activity. Signal values, ranges, missing values, tie-breaking, and behavior for Tier 3 must be tested. A Tier 3 forced-zero rule overrides any high upstream scores.

## Domain shift and retrieval metrics (later/staged work)

- **PDSS (FR3):** proposed as the mean candidate `d_AD` divided by a within-reference baseline. The source analysis suggests mean reference-cloud distance; the PP1 inventory flags a near-zero denominator concern. The denominator, robustness alternatives, and interpretation must be approved before computing a ratio. A ratio is not automatically constrained to be at least 1.
- **PARRS (FR6):** \(EF@1\%_{Tier1}/EF@1\%_{FullPool}\). It measures a relative enrichment change only under a specified held-out positive set and evaluation universe. Define behavior when either enrichment is undefined or zero, and report numerator/denominator with the ratio.
- **EF@1%:** enrichment in the top one percent relative to the prevalence in the declared evaluation universe. Define rounding of the one-percent cutoff and the candidate-positive matching rule.
- **Recall@K:** fraction of the declared held-out AOP positives retrieved in the first K candidates; report K and denominator.
- **MRR:** mean reciprocal rank of relevant held-out positives under a clearly defined query/ranking setup. The project must resolve whether the unit is per positive query or one aggregate list before reporting.
- **ARR (FR5):** fraction of a predictor's top-50 nominees that fall in Tier 3. Specify tie handling and what happens when fewer than 50 candidates are scored.

Never compute retrieval metrics against dummy signals or describe planned metrics as achieved findings. The held-out set must be separated from the model training/reference data under the agreed MMseqs2 40% identity procedure; preserve the filter report and exact inputs.

## Evidence flags (FR7)

The proposed traffic-light mapping is GREEN for Tier 1, AMBER for Tier 2, and RED for Tier 3/abstained. BCS belongs to a predictor and should be shown as predictor reliability context, not as an intrinsic property of the peptide. The inventory specifies a warning below BCS 0.5; HIGH/MEDIUM cutoffs are provisional and require C3-owner confirmation. Dummy values must be visibly labelled in each card and export.
