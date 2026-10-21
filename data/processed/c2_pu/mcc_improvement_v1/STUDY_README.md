# MCC reliability study v1

Reports use collision-safe `study__<UTC timestamp>` directories here. Local model
checkpoints, resolved configurations, scalers and memberships are under the same
study ID in `data/interim/c2_pu/mcc_improvement_v1/` and excluded from Git. Keep
these ignored bytes together with the reports; Git alone does not preserve models.

## Reproduce from the repository root (PowerShell)

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
$py = (Resolve-Path .venv/Scripts/python.exe).Path
# Use the study's environment_requirements.txt to recreate exact package versions.
$study = (& $py -m plantaox.c2_pu.mcc_study init | Select-Object -Last 1).Trim()
& $py -m plantaox.c2_pu.mcc_study diagnose --study $study
& $py -m plantaox.c2_pu.mcc_study pilot --study $study
# Inspect compute_estimate.json before expansion; no paid resources are needed.
& $py -m plantaox.c2_pu.mcc_study expand --study $study
& $py -m plantaox.c2_pu.mcc_study evaluate --study $study
# Optional predeclared exploratory amendment; reports both policies without picking a winner:
& $py -m plantaox.c2_pu.mcc_study followup --study $study
& $py -m plantaox.c2_pu.mcc_study evaluate --study $study
& $py -m plantaox.c2_pu.mcc_study reproduce --study $study
& $py -m pytest tests/c2_pu/test_mcc_study.py tests/c2_pu/test_nnpu_risk.py tests/c2_pu/test_corrective_nnpu.py tests/c2_pu/test_baseline_evaluation.py tests/c2_pu/test_experiment_data.py tests/c2_pu/test_models.py tests/c2_pu/test_seeding.py tests/c2_pu/test_run_recorder.py -q -p no:cacheprovider > "$study/focused_tests.log"
# Copies historical inputs before running tests that can regenerate artifacts:
& $py -m plantaox.c2_pu.mcc_study_qa --study $study
& $py -m plantaox.c2_pu.mcc_study finalize --study $study
```

`pilot` and `expand` resume completed ledger entries. Do not reuse a study after
changing its training code or experimental plan: initialize a new ID instead.
`evaluate` loads saved selected checkpoints and verifies their hashes. It runs
only after representation selection has been frozen, and never changes training.
Checkpoint bytes include save timestamps and need not be byte-identical across
retraining; deterministic predictions/weights are the relevant reproduction test.

## Primary outputs

- `FINAL_SCIENTIFIC_REPORT.md`: historical fold0 comparison and dependent fold/seed variability.
- `all_evaluations.csv`: every candidate, sensitivity/comparator fit and both threshold policies.
- `all_predictions.csv`: peptide-level raw/bounded scores; no score reversal.
- `training_ledger.json`: validation-only selection criteria, full histories and local checkpoint paths/hashes.
- `selection_frozen.json`: fold-specific decisions before retrospective scoring.
- `baseline_reproduction.json`, `baseline_alignment_and_orientation.json`: five-model read-only reproduction.
- `descriptor_shift_statistics.csv`, composition, PCA/overlap, matched diagnostics and publication errors.
- `THRESHOLD_INVESTIGATION.md`: why assay-MCC threshold selection is not identifiable.
- `plots/`: exportable SVG/PNG scientific figures.
- `REPRODUCIBILITY_AND_TEST_REPORT.md`: verification results, failures and limitations.
- `FILE_MANIFEST.csv`: exact study-created files and hashes (large ignored models included).

All control results are retrospective assay-supported comparison, not independent
validation. C1/C2/C3 proxy results are explicitly distinguished from these metrics.
Model selection cannot use the external assay metrics even if they improve.

## Reference review

All 15 Markdown files in `src/plantaox/c2_pu/docs/` and extractable text from all 61
proposal PDF pages were reviewed. Proposal image-only diagrams were not visually
inspected. Latest freeze/handover and actual resolved configurations take precedence
over stale historical status passages. No reference files or frozen inputs were edited.
