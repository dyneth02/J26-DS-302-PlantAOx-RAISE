# C2 PU-AOP: MLflow experiment view

A separate, read-only MLflow view of C2 training runs: the accepted SO4 runs
from the frozen `c2_pp1_freeze_v1` release, plus the post-freeze MCC
reliability study. It does not retrain anything, does not touch `data/` or
`src/`, and is not connected to the React/FastAPI dashboard.

## What is imported

| Experiment | Runs |
|---|---|
| SO4 Baseline Comparison | M1 PN, M2 direct-clamped nnPU, M3 corrective nnPU, M4 Two-Step PU, M5 PU-Bagging |
| SO4 nnPU Prior Sensitivity | pi = 0.05, 0.10 (accepted), 0.20 |
| SO4 Evidence-Weighted Curriculum | parent run + nested stages C1, C2, C3; plus the first attempt, which crashed on a Windows file lock and is shown as FAILED (not accepted) |
| MCC Reliability Study (`study__...`) | all 161 fits from `all_evaluations.csv` (5 methods x 3 representations x 5 folds x 3 seeds, plus sensitivity and follow-up runs) and one "Study reports and figures" run holding the study's reports and plots |

The MCC study is post-freeze research, not part of the PP1 release; its runs
are tagged `provenance=backfilled_from_mcc_study` and both threshold policies
are logged (`eval.fixed.*`, `eval.heuristic.*`). Its external metrics reuse the
same 38 controls, so they are retrospective, not independent validation.

Each run has its hyperparameters, per-epoch training curves (neural models
only; Two-Step PU and PU-Bagging are single-fit), the accepted external-control
metrics (`eval.*`), and descriptive unlabeled-pool scoring (`unlabeled_pool_behaviour.*`,
which is not a false-positive rate). Only the runs referenced by the accepted
summaries are imported; the other timestamped directories under
`data/interim/c2_pu` are test-suite reruns. Baseline checkpoints are re-hashed
against the freeze manifest and tagged `checkpoint_integrity`. Every run is
tagged `provenance=backfilled_from_frozen_pp1` and keeps its original date.

## Setup (once, needs internet)

```powershell
uv venv mlflow_tracking\.venv --python .uv-python\cpython-3.11.14-windows-x86_64-none\python.exe
uv pip install --python mlflow_tracking\.venv\Scripts\python.exe -r mlflow_tracking\requirements.txt
```

## Import and open (offline)

```powershell
mlflow_tracking\.venv\Scripts\python.exe mlflow_tracking\backfill_fr4_runs.py
mlflow_tracking\.venv\Scripts\mlflow.exe ui --backend-store-uri sqlite:///mlflow_tracking/mlflow.db --port 5000 --workers 1
```

Open http://127.0.0.1:5000. Re-running the import is safe (already-imported
runs are skipped); add `--rebuild` to wipe and re-import. `--workers 1` avoids
a Windows socket error in MLflow's default multi-worker mode.

Requires the Git-ignored `data/interim/c2_pu` run directories (per-epoch
metrics and configs); see `C2_PP1_HANDOVER.md` for recovering them.

## Demo tips

- Open an experiment, then the **Runs** tab with the chart view. Type
  `eval.mcc` or `eval.auroc` into "Search metric charts" to show one metric
  across all five models instead of all 65 charts.
- Close the "MLflow Assistant" panel: it needs an external AI service and
  will not work offline.
- In the curriculum experiment, the parent run's `stage_trajectory.*` charts
  show C1, C2, C3 as steps 1-3 on a single chart.
- In the MCC study, paste this into the run search box to keep only the 75
  fits chosen by inner validation (excludes sensitivity runs and the summary run):
  `tags.selected = 'true' and tags.phase = 'main'`
  Then use **Group by** -> `method` (or `representation`) and search the charts
  for `eval.fixed.mcc`. The grouped values reproduce the five-folds x
  three-seeds table in `FINAL_SCIENTIFIC_REPORT.md`; the spread is across
  dependent runs, not a confidence interval.
- The UI loads runs 100 at a time and charts only the visible (eye icon) runs,
  so filter before comparing large groups.
