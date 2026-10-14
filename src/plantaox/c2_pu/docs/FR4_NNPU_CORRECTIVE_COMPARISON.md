# FR4 nnPU Corrective-Optimization Comparison

**Date:** 15 October 2026  
**Status:** Controlled fold-0 follow-up complete; Task 4.3 PASS remains unchanged.

## Purpose and method

The accepted direct-clamped nnPU run crossed the negative-risk threshold in about 99% of updates, so
its C1-unlabeled term usually had zero gradient. This follow-up implements Kiryo et al.'s corrective
optimization as the separately named `corrective_beta_gamma` variant:

\[
R_n=R_u^- - \pi R_p^-,\qquad
L_{train}=\begin{cases}
\pi R_p^+ + R_n & R_n\ge -\beta\\
-\gamma R_n & R_n< -\beta
\end{cases}
\]

The monitoring and checkpoint-selection quantity remains
\(R_{reported}=\pi R_p^+ + \max(0,R_n)\). Optimizer loss and reported nnPU risk are logged separately.
Parameters were fixed before training at π=0.10, β=0.0, γ=1.0; no search was performed.

## Controlled configuration

Both variants use fold 0, E1+E2 positives, C1 as unlabeled, the accepted 495-dimensional fused cache,
the 495→128→64→1 `BinaryMlp`, Adam at 0.001, seed 42, maximum 100 epochs, and patience 10.
The accepted run's immutable `resolved_config.json` records batch size 32 and weight decay 0.0. Those
values were reused, although the follow-up brief stated 64 and 0.0001, because matching the actual
accepted artifact is required for a one-variable optimization-rule comparison.

Dataset membership is unchanged: 331 E1 + 273 E2 = 604 training positives; 48 E1 + 58 E2 = 106
validation positives; 3,220 training C1 and 568 validation C1 sequences. Held-out positives, C2, C3,
and the external inactive control were not used for training, checkpoint selection, or tuning.

## Results

| Metric | Direct-clamped nnPU | Corrective nnPU |
|---|---:|---:|
| Prior π | 0.10 | 0.10 |
| Beta / Gamma | N/A | 0.0 / 1.0 |
| Training epochs | 26 | 27 |
| Best epoch (zero-based) | 15 | 16 |
| Best validation nnPU risk | 0.0001843 | 0.0630219 |
| Negative-risk threshold frequency | 98.63% | 53.25% |
| Final-five threshold frequency | 99.41% | 52.87% |
| Negative-risk gradient handling | Zero when clamped | Corrective ascent |
| E1 validation median score | 1.0000 | 0.6824 |
| E1 validation fraction >0.5 | 100.00% | 70.83% |
| E2 validation median score | 0.99999 | 0.5338 |
| E2 validation fraction >0.5 | 100.00% | 53.45% |
| C1 validation median score | 0.03785 | 0.01684 |
| C1 validation fraction >0.5 | 35.56% | 1.76% |
| Training stability | Finite; strongly saturated positives | Finite; no score saturation >0.99 |

The corrective run executed 2,727 optimizer updates. Its reported training risk moved from 0.13847 in
epoch 0 to 0.06375 in the final epoch; validation risk was 0.07895 initially, reached its selected
minimum at epoch 16, and ended at 0.08914. The branch-specific optimizer loss stayed finite throughout
(epoch means 0.05086–0.09166). Best and last checkpoints reload successfully and produce finite,
bounded scores.

## Interpretation

Corrective optimization materially changes the dynamics. With β=0, the threshold condition is the
same condition that triggers direct clamping, but its frequency is not a success metric by itself.
The important change is gradient handling: approximately 53% of updates now use `-γR_n`, so C1
influences optimization by pushing the estimated negative risk upward. In the direct model, roughly
99% of updates suppress that unlabeled gradient.

Predictions changed substantially. The corrective model is less saturated and assigns far fewer C1
validation rows scores above 0.5, while also lowering E1/E2 positive scores. This is evidence that the
optimizer no longer behaves like positive-risk-only training; it is not evidence of better biological
classification. C1 is unlabeled, the validation objective is a PU surrogate under an assumed prior,
and raw nnPU risks from different optimization trajectories do not establish real-world superiority.

The result supports retaining corrective nnPU as a distinct candidate in Task 4.5 alongside the
accepted direct-clamped model. Task 4.5 should compare both using its pre-specified evaluation policy,
without treating C1 as confirmed negative or choosing between variants from surrogate risk alone.

## Integrity and artifacts

- Corrective summary: `data/processed/c2_pu/fr4_nnpu_corrective_fold0_summary.json`
- Learning curve: `data/processed/c2_pu/fr4_nnpu_corrective_fold0_learning_curve.svg`
- Run directory: `data/interim/c2_pu/fr4_nnpu_corrective_runs/fr4_nnpu_corrective_fold0__20261014T221912Z`
- Best checkpoint SHA-256: `d4446b4dff90b1d1ce3d2c03fa314bd0a65134e6621cf3c01f3a9332442307dd`
- Last checkpoint SHA-256: `c89227cf13a70ba7c94ab45e391e95f72352d3a0de7010fab538a3f289e592f5`
- Accepted direct summary remained SHA-256 `2ada36eaa4b865280488f0c3828b7a4b788bf9c86e40fad271a5a0d42983f5cb`.
- Frozen manifest hashes remained: FR1 `88f14bb9...c27f2`; FR2 `dbd8755a...4e2b4`; FR3 cache manifest `81c87075...8d97a`.

Focused checks cover the normal objective, corrective gradient direction, finite branch values,
unchanged direct-clamped gradient behavior, short training, and checkpoint reload. Full-suite results
are recorded in `IMPLEMENTATION_STATUS.md` after execution.

## Limitations

This is one fold, one seed, one assumed prior, and one untuned β/γ setting. E2 remains provisional;
positive-selection bias and the FR1/C1 source-distribution mismatch remain unresolved. Scores are model
outputs, not calibrated antioxidant probabilities. Technical completion does not imply scientific or
supervisor approval.
