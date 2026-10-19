# C4 PP1 Slides — five-slide content and speaker notes

**All mock items are explicitly marked MOCK below.** The current cloud, SIM_C1, PROB_C2, BCS, derived scores/ranks/cards, and demo injections are synthetic demonstrations.

## Slide 1 — Why screen plant digestomes?

**On-slide:** Four reviewed proteomes → sequential in-silico digestion → peptide candidates → applicability-domain screening. **MOCK reference cloud + MOCK signals: demonstration only.** Proposal's per-plant candidate estimate is not assumed; use measured funnel counts.

**Speaker notes:** Explain the objective as a candidate-retrieval prototype and distinguish a technical pipeline from biological validation. Cite reviewed-only UniProt scope.

## Slide 2 — Reproducible candidate generation (FR1)

**On-slide:** Soybean 13,468 · Rice 140,813 · Rapeseed 4,910 · Olive 565 unique plant candidates; 152,259 globally unique. Filter: 3–20 AA, at least two residue types, standard alphabet. **MOCK downstream cloud/signals are not used for these FR1 counts.**

**Speaker notes:** Pyteomics uses pepsin pH 1.3 as nearest installed rule to proposed pH 1.2, then trypsin. Exact dedup preserves parent provenance. BIOPEP spot-check is deferred.

## Slide 3 — Applicability domain (FR2; MOCK cloud)

**On-slide:** **MOCK cloud, N=500.** ESM-2 handoff: 152,259 × 1,280; layer-33 mean residue pooling (C4 assumption). `mu=0.0185099002`, `sigma=0.0097886926`, `t1=0.0282985928`, `t2=0.0380872854`. Baseline tiers: Olive 51.50/33.45/15.04%; Rapeseed 50.12/32.69/17.19%; Rice 56.99/25.37/17.64%; Soybean 55.22/29.63/15.15% (T1/T2/T3).

**Speaker notes:** Distances and thresholds are calibrated against synthetic mock sequences. Mean-centering is a separate labelled sensitivity; no production threshold changes were made.

## Slide 4 — Evidence cards (MOCK signals + MOCK cloud)

**On-slide:** Example card `MAHQWV`, Soybean Tier 1, CS=0.812150 (**MOCK signals/cloud**). Example abstention `AGMEEVDMDEEVRPEF`, Rice Tier 3, CS=0, injected demonstration (**MOCK**). GREEN/AMBER = Tier 1/2; RED appears only for abstentions.

**Speaker notes:** CS and BCS are pipeline placeholders. Tier 3 is forced to zero and routed to abstention. A high injected PROB_C2 is not evidence of activity.

## Slide 5 — Limits and next evidence

**On-slide:** **Current reference cloud: MOCK. Current SIM_C1 / PROB_C2 / BCS: MOCK.** Real cloud sequence handoff staged (912 C2-derived E1/E2 sequences; provisional source); Colab embeddings pending. Next: C1 AOP-BenchPos replacement, signal-owner outputs, supervisor review, held-out evaluation, biological validation.

**Speaker notes:** Layer/pooling is an unconfirmed C4 assumption. The cloud mean length is 12.14 AA vs candidate mean 7.631 AA. These data do not establish activity, generalization, safety, or efficacy. No retrieval performance metric is derived from mock inputs.

## Q&A preparation

- **Why mock?** Owner-supplied signal outputs and a validated positive cloud were not available for the current production run. The synthetic values make schemas, determinism, abstention, and UI behavior testable; they are marked MOCK. A 912-sequence provisional C2-derived handoff is staged for Colab.
- **Is `d_AD` circular?** It is a geometric distance to a reference cloud, not an activity label. With a composition-biased synthetic cloud, it is only a software demonstration and cannot validate biological proximity.
- **Raw vs mean-centered tiers?** Production uses uncentered embeddings. The separate feature-mean subtraction sensitivity materially shifts tiers and is not selected/tuned for presentation; it signals representation sensitivity.
- **Pepsin vs known AOPs?** Pepsin pH 1.3 is the nearest pyteomics rule to proposed pH 1.2. Aromatic cleavage may reduce recovery of known AOP sequences. BIOPEP spot-check and recoverability check remain deferred.
- **Why counts differ from 5K–50K?** Reviewed-only protein scope and measured digestion/filter/dedup funnel produce the reported counts; the proposal's estimate is not forced or padded.
- **Length mismatch?** MOCK cloud mean is 12.14 AA and candidates mean 7.631 AA; distance/tier diagnostics may reflect this shift. Report it as a limitation, not evidence of biological domain quality.
