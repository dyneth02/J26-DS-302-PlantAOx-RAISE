# Component 02 PP1 handover

## What this component does

Component 02 builds a positive-unlabeled antioxidant-peptide research prototype:

1. **FR1** curates E1/E2 positive evidence and creates five homology-controlled GraphPart folds.
2. **FR2** creates three unlabeled challenge pools: C1 random/uncharacterized peptides, C2 bioactive peptides without the project AOP annotation, and fold-specific C3 embedding-nearest challenges. The assay-inactive controls remain separate and evaluation-only.
3. **FR3** computes 15 descriptors, loads 480-dimensional ESM-2 embeddings, fuses them into 495 features, and applies fold-specific scalers fitted only on training positives.
4. **FR4** provides PN, direct-clamped nnPU, corrective nnPU, Two-Step PU, PU-Bagging, a common fold-0 evaluation, and an evidence-weighted corrective-nnPU C1→C2→C3 curriculum.

The frozen dataset identifiers are `pp1_baseline_v1` and `pp2_baseline_v1`. The implementation freeze is `c2_pp1_freeze_v1`, referenced by the annotated Git tag `c2-pp1-v1`.

## Environment

The verified host used Python 3.11.14 and the package versions recorded in `data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json`. Project dependencies are declared in `requirements.txt`; it is not a fully pinned lockfile. The repaired project interpreter is:

```text
.venv/Scripts/python.exe
```

Set `PYTHONPATH` to `src` when running without installing the package.

## Read-only offline verification

From the repository root in PowerShell:

```powershell
$py=(Resolve-Path '.venv\Scripts\python.exe').Path
$env:PYTHONPATH=(Resolve-Path 'src').Path
& $py -m plantaox.c2_pu.pp1_freeze verify --manifest data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json
& $py -m pytest tests/c2_pu/test_pp1_freeze.py -q
```

Expected verifier status is `PASS`, with 170 inventory records, 10 valid PP1 frozen files, 28 valid PP2 frozen files, a `9356 × 495` fold-0 cache, 2,000 fold-0 C3 rows, zero external-control overlap, and finite bounded inference from the PN, Stage-C1, and Stage-C3 checkpoints.

Verify the preserved ignored bytes without writing to the backup:

```powershell
& $py -m plantaox.c2_pu.pp1_freeze verify-backup-directory --manifest data/processed/c2_pu/C2_PP1_FREEZE_MANIFEST.json --backup-root 'C:\Users\metal\Documents\SLIIT Research\Data\C2-PP1-baseline-data'
```

The accepted FR3 demonstration command is:

```powershell
& $py -m plantaox.c2_pu.run fr3-demo
```

That command is offline and uses cached embeddings/features, but it rewrites `fr3_demo_output.json` and appends provenance. Use the read-only freeze verifier for routine integrity checks. Use `fr3-demo` only when intentionally demonstrating the accepted feature walkthrough.

## Required artifacts

Use `data/processed/c2_pu/C2_PP1_ARTIFACT_INVENTORY.csv` as the authoritative file list. Every entry has a relative path, byte size, SHA-256, Git disposition, retention class, and recovery note.

Important local Git-ignored files include:

- `data/interim/c2_pu/fr3_embeddings.npz`
- `data/interim/c2_pu/fr3_fold0_scaled_features.npz`
- accepted run directories under `data/interim/c2_pu/fr4_*_runs/`
- curriculum checkpoints under `data/interim/c2_pu/fr4_curriculum_runs/fr4_curriculum_fold0__20261015T103556Z/`

The accepted weighted C1 reference is the existing Stage-C1 best checkpoint, SHA-256 `f566c06314e1b243124abf49e660b3979f3d086e51b19ad9f2d1b0929494f7d4`. The final selected Stage-C3 best checkpoint is SHA-256 `f2775fa2855454098b58e35431a18cbb6081f9c777bd7880720bb25dfd715aa6`; its epoch 0 is post-update after 63 C3 steps.

The 56 essential ignored artifacts are preserved in the owner-supplied external data copy at `C:\Users\metal\Documents\SLIIT Research\Data\C2-PP1-baseline-data`. The freeze verifier confirmed all 56 files and 39,103,768 bytes against the inventory SHA-256 values. Preserve or migrate this directory together with the Git tag; after any migration, run `verify-backup-directory` again. Do not commit checkpoints or arrays to Git and do not regenerate a missing accepted checkpoint merely to satisfy a checksum.

## Results and figures

- Five-model evaluation: `data/processed/c2_pu/fr4_baseline_evaluation_fold0.json`
- Comparison table: `data/processed/c2_pu/fr4_baseline_comparison_fold0.csv`
- Evaluation figures: `fr4_baseline_mcc_fold0.svg`, `fr4_baseline_auprc_fold0.svg`, `fr4_baseline_challenge_scores_fold0.svg`
- External-control diagnostic: `fr4_external_control_diagnostic.json` and `FR4_EXTERNAL_CONTROL_DIAGNOSTIC.md`
- Curriculum: `fr4_curriculum_fold0_summary.json` and `FR4_CURRICULUM_PROTOTYPE_REPORT.md`
- Matched PP1 table/figure: `fr4_pp1_matched_curriculum_fold0.csv` and `.svg`
- Methodological audit: `FR4_PP1_PRE_FREEZE_METHOD_AUDIT.md`
- Freeze detail: `C2_PP1_FREEZE_REPORT.md`

## What the demonstration proves

It proves that the accepted data manifests, feature cache, fold-specific C3 selection, model loaders, checkpoint lineage, inference, preliminary evaluation, and curriculum implementation are reproducible in the verified local environment.

It does not prove reliable antioxidant discrimination. All five Task 4.5 MCC values were negative and all AUROCs were below 0.5 on the 124-positive/38-control assay-supported view. No curriculum stage reliably separated the 38 controls. C1/C2/C3 are unlabeled and cannot supply confirmed specificity. Scores are not calibrated biological probabilities.

## Continuing after PP1

Do not modify accepted files or runs. Branch from `c2-pp1-v1` and create new experiment IDs and versioned artifacts. Begin with the existing shortcut-learning/source-bias diagnostic plan and broader assay-matched controls before multi-fold reliability claims. FR6/RNIS, calibration, and scientific validation remain unfinished future milestones.

Pending scientific decisions are listed in the release manifest and freeze report. Technical acceptance must remain separate from supervisor/scientific approval.
