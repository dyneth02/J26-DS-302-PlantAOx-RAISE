# PP1 Supervisor Demo Walkthrough — Component 02 (PU-AOP)

A suggested sequence for presenting the Component 02 PP1 demonstration. Each step
names what's actually being shown and the exact caveat to state alongside it —
this is implementation evidence, not a claim of scientific validation.

Start both servers first (`docs/PP1_DASHBOARD_SETUP.md`), then open
http://localhost:5173.

## 1. Platform overview (`/`)

**Show:** the shared shell — four components listed, only C2 marked
"Implemented." **Say:** "This is a shared platform built so my three teammates
can add their components independently. I've implemented Component 02 end-to-end
against its accepted PP1 freeze; C1/C3/C4 are shown for ownership context only."

## 2. Component 02 overview (`/c2`)

**Show:** research title, freeze badge ("FROZEN — READY WITH LIMITATIONS"),
freeze id `c2_pp1_freeze_v1` / tag `c2-pp1-v1`, FR1–FR4 milestone summaries, data
counts (1,205 accepted positives, 834 after homology control, 3,788/2,000/2,325
challenge-pool sequences, 38 external controls, 495-dim features, 5 baseline
models). **Say:** "Technical status and scientific status are reported
separately on this page — technically this is accepted and reproducible;
scientifically, reliable antioxidant-activity discrimination is not yet
established. That's a direct quote from the frozen manifest, not my summary."

## 3. FR1 — Data curation (`/c2/fr1`)

**Show:** 1,205 provisional positives (670 E1 / 535 E2), 179 cross-source
conflicts excluded, CD-HIT clustering (925 clusters), the GraphPart 5-fold
distribution chart. **Say:** "E2 is provisional — Multi-AOP-only, no
per-record assay metadata, pending supervisor review. The three open supervisor
approvals below are still genuinely open, not resolved by this dashboard."

## 4. FR2 — Challenge pools (`/c2/fr2`)

**Show:** C1/C2/C3/external-control pool cards, then select a GraphPart fold in
the C3 explorer and show the top-10 hardest challenges by cosine similarity.
**Say:** "C1, C2 and C3 are unlabeled pools, not confirmed non-antioxidant
peptides — that's enforced in the pool descriptions themselves. The fold
selector is important: C3's full 2,325-sequence union is *not* a valid
per-fold challenge set on its own; this page calls the same
`curation.c3.load_fold_challenges(path, fold_id)` function the training code
uses, specifically to avoid that mistake."

## 5. FR3 — Feature workbench (`/c2/fr3`)

**Show:** select 2–3 of the seven accepted demonstration peptides (e.g. an E1
positive, a C1 decoy, a C3 hard challenge). Point out the live-computed 15
physicochemical descriptors and the "ESM-2 embedding cached" badge. **Say:**
"These are the project's own seven accepted demo peptides. Descriptors are
computed live using the project's existing, deterministic descriptor
functions — no new ESM-2 inference happens on this page; the 480-dim embedding
is read from the cached file, and fusion to 495 dims uses that fold's
training-positives-only scaler."

## 6. FR4 — Model comparison (`/c2/fr4`)

**Show:** the metric toggle (MCC / AUROC / AP / F1) and point out every bar is
rendered in the "negative/below-threshold" color; select 2 models with the
checkboxes to show the side-by-side comparison panel. **Say:** "All five
baselines show negative MCC and sub-0.5 AUROC on the assay-supported
evaluation — that's not hidden or re-scaled, it's the headline result of this
milestone. The challenge-pool scoring table below is explicitly labeled
descriptive, not a false-positive rate, since C1/C2 aren't confirmed
negatives."

## 7. Curriculum (`/c2/curriculum`)

**Show:** the C1 → C2 → C3 stage progression and the positive-recovery vs.
external-MCC/AUROC line chart. **Say:** "Checkpoint selection at every stage —
including C2 and C3 — uses a C1-based surrogate validation risk, not a
stage-matched signal, and this is a single weighted run, not a controlled
ablation against an unweighted baseline. External MCC stays negative at every
stage; later stages trade off positive recovery against control
discrimination, they don't demonstrate improving reliability."

## 8. Evidence & reproducibility (`/c2/evidence`)

**Show:** artifact status (170/170 tracked artifacts present on this
checkout), the open supervisor decisions list. **Say:** "This is a fast
existence check; the authoritative byte-for-byte verification is the
project's own `pp1_freeze verify` command, which I ran offline before this
demo — not something the web app re-runs on every page load, since it loads
every checkpoint and would be far too slow as a request handler."

## Anticipated questions

- **"Is this model good?"** — No. Say so directly: negative MCC, sub-0.5 AUROC,
  on the assay-supported evaluation. This milestone establishes a reproducible
  technical prototype and an evidence-tiered, leakage-audited data pipeline —
  not a validated classifier.
- **"Why can't I run inference on a new sequence?"** — Deliberately out of
  scope for this PP1 build. Live inference would need a stricter review of
  checkpoint-loading and scaling correctness than this milestone covers; the
  dashboard surfaces the accepted, already-computed evaluation results instead
  of attempting new inference without a documented and tested feature-generation
  path, with "model loading fails explicitly, never a random fallback" as a hard
  non-negotiable.
- **"What happens if I clone this on another machine?"** — FR1/FR2 pages work
  immediately (their data is Git-tracked). FR3/FR4/curriculum/evidence need the
  Git-ignored `data/interim/c2_pu/` caches and checkpoints, recoverable from the
  location documented in `src/plantaox/c2_pu/docs/C2_PP1_HANDOVER.md`; without
  them, those pages show a clear "artifact unavailable" panel rather than
  fabricated numbers.
