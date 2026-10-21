# Reproducibility and test report

All 161 experimental fits and 322 metric views were checked against persisted peptide predictions.
There are 75 selected main fold/seed evaluations, plus all candidates and follow-ups.
Five additional same-seed retraining checks (one per algorithm) reproduced every prediction
exactly on all scored training/validation/test/challenge/control rows. Checkpoints were
restored twice at fit time; timestamp-bearing serialized hashes need not match across fits.

Focused final suite: **126 passed**, covering arithmetic/orientation, invalid labels,
five-fold isolation, scaler poisoning, selection poisoning, C2 mixture boundaries,
deterministic seeds, corrective gradients, checkpoints and existing evaluation.
See focused_tests.log. Historical full C2 suite in a disposable copy:
**5 failed, 684 passed, 2 skipped in 506.91s (0:08:26)**. Full log and command are retained. Review its individual
failures separately: in this execution WSL-dependent ESM/needleall checks report
E_ACCESSDENIED, and the release verifier sees a non-Git copy after writing tests
append copied provenance.
These failures were not converted to passes or hidden by weakened assertions.

Canonical read-only release verification before and after the study reports exactly
one pre-existing file mismatch: the method-audit Markdown has CRLF line endings.
Its LF-normalized bytes equal the frozen tag and inventory SHA-256. All **10 PP1
and 28 PP2 frozen files** verify their hashes. Every accepted inventory path was
snapshotted before diagnostics and remains byte-for-byte unchanged after all work.
No backup directory was written and no remote push occurred. A full release-PASS
claim for this working checkout is intentionally not made.

One initial setup attempt failed before fitting because the first guard rejected
repeated C1 source IDs. The corrected guard verifies identical sequence, pool,
tier and fold before unique-cache alignment. Its empty directory is retained in
setup_failures.json. No failed scientific fit was excluded. All model runs completed.

Source snapshots at initialization/per-fit record on-disk code. New reporting/QA
and orchestration helpers were refined during execution; imported modules can
precede an on-disk snapshot. Original accepted trainers/risk functions were never
edited. Final source copies/hashes plus exact same-seed five-method retraining
provide a reproducible final implementation; do not interpret per-fit disk hashes
as Python interpreter tracing. The exploratory C2 amendment is explicitly dated
after main retrospective inspection. No final-control scores selected its policy.

Nine SVG figures parse successfully. MCC, feature comparison and ROC/PR PNGs were
visually inspected for labels/layout. All outputs retain fixed thresholds, raw
Elkan-Noto ranking scores and separately clipped decision scores.

Reproduction commands: ../STUDY_README.md. Exact packages: environment_requirements.txt.
The raw cached feature SHA, GraphPart identities, seeds, all transformations,
membership, optimizer histories, runtime and checkpoint hashes are retained.
Statistical bootstrap intervals are conditional peptide intervals, not an estimate
of independent publication/family/model-selection uncertainty. No independent
assay-matched panel was acquired; candidate search/access limitations are logged.
