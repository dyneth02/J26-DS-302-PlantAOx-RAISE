# PP1 Manually Inspected Variant Examples

**Status:** PASS  
**Classification:** Software-testing evidence only  
**Warning:** Dummy predictor scores are not scientific AOP results.

The six examples below were selected manually and checked row by row. The inspection was then independently revalidated against the frozen perturbation rules, Biopython BLOSUM62, and the deterministic dummy scorer.

| Type | Variant | Original | Edit | Perturbed | BLOSUM62 | Original score | Perturbed score | DeltaScore |
|---|---|---|---:|---|---:|---:|---:|---:|
| P1 | `C3-ANOX-000205-P1-01-WA` | `WHH` | W1A | `AHH` | N/A | 0.45 | 0.3 | 0.15 |
| P1 | `C3-ANOX-000467-P1-24-YA` | `SFGAKNAVKNGLQKLRNQCQANNYQGPFCDIFKKNP` | Y24A | `SFGAKNAVKNGLQKLRNQCQANNAQGPFCDIFKKNP` | N/A | 0.46996996996997 | 0.435735735735736 | 0.0342342342342342 |
| P2 | `C3-MAOP-AOPP-001031-P2-01-LI` | `LAQGTFLQPHQ` | L1I | `IAQGTFLQPHQ` | 2 | 0.542424242424242 | 0.540909090909091 | 0.00151515151515158 |
| P2 | `C3-ANOX-000074-P2-06-VI` | `PMDYMVT` | V6I | `PMDYMIT` | 3 | 0.725 | 0.617857142857143 | 0.107142857142857 |
| P3 | `C3-MAOP-ANOXPP-000940-P3-01-LQ` | `LRTLPM` | L1Q | `QRTLPM` | N/A | 0.623809523809524 | 0.633333333333333 | -0.00952380952380949 |
| P3 | `C3-ANOX-000467-P3-36-PG` | `SFGAKNAVKNGLQKLRNQCQANNYQGPFCDIFKKNP` | P36G | `SFGAKNAVKNGLQKLRNQCQANNYQGPFCDIFKKNG` | N/A | 0.46996996996997 | 0.451051051051051 | 0.0189189189189189 |

## Checks performed

- Declared one-based position equals the only changed position.
- Original and substituted residues match their sequences at that position.
- The perturbed sequence is exactly reconstructed by the declared edit.
- Sequence length is unchanged.
- Original, perturbed, and DeltaScore values reproduce independently.
- P1 examples follow redox-to-alanine rules.
- P2 examples reproduce the selected residue and BLOSUM62 score.
- P3 examples retain the configured master seed and random metadata.
