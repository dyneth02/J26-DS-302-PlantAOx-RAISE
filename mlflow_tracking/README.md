# C2 PU-AOP: MLflow experiment view (SO4)

A separate, read-only MLflow view of the accepted SO4 runs from the frozen
`c2_pp1_freeze_v1` release. It does not retrain anything, does not touch
`data/` or `src/`, and is not connected to the React/FastAPI dashboard.

## What is imported

| Experiment | Runs |
|---|---|
| SO4 Baseline Comparison | M1 PN, M2 direct-clamped nnPU, M3 corrective nnPU, M4 Two-Step PU, M5 PU-Bagging |
| SO4 nnPU Prior Sensitivity | pi = 0.05, 0.10 (accepted), 0.20 |
| SO4 Evidence-Weighted Curriculum | parent run + nested stages C1, C2, C3 |

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
