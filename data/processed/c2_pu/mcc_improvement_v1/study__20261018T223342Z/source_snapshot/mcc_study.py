"""Isolated, staged MCC reliability study; historical artifacts are read-only.

Run ``python -m plantaox.c2_pu.mcc_study --help``. Selection and retrospective
evaluation are separate commands. C1 numeric zero is always provisional.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import pandas as pd

from plantaox.c2_pu.baseline_evaluation import classification_metrics
from plantaox.c2_pu.common.feature_cache import sha256_of
from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import (
    ExperimentData, PoolData, _slice_features, assert_no_cross_subset_overlap,
)
from plantaox.c2_pu.run_recorder import create_run_dir, write_resolved_config, RunContext

PROCESSED = Path('data/processed/c2_pu')
INTERIM = Path('data/interim/c2_pu')
REPORTS = PROCESSED / 'mcc_improvement_v1'
RUNS = INTERIM / 'mcc_improvement_v1'
METHODS = ('PN', 'Direct', 'Corrective', 'TwoStep', 'Bagging')
REPRESENTATIONS = ('descriptors', 'esm', 'fused')


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + '\n', encoding='utf-8')


def inventory_snapshot() -> dict:
    inventory = pd.read_csv(PROCESSED / 'C2_PP1_ARTIFACT_INVENTORY.csv')
    paths = set(inventory.path)
    paths.update(str(p) for p in (PROCESSED / 'frozen').rglob('*') if p.is_file())
    return {p: sha256_of(Path(p)) if Path(p).is_file() else None for p in sorted(paths)}


def assert_preserved(before: dict):
    changed = [p for p, h in before.items()
               if (sha256_of(Path(p)) if Path(p).is_file() else None) != h]
    if changed:
        raise RuntimeError(f'Accepted artifact bytes changed: {changed}')


def load_raw():
    manifest = json.loads((PROCESSED / 'fr3_feature_cache_manifest.json').read_text())
    path = INTERIM / 'fr3_fused_raw.npz'
    if sha256_of(path) != manifest['input_file_hashes']['fused_raw_cache']:
        raise ValueError('Raw cache checksum mismatch')
    with np.load(path, allow_pickle=False) as z:
        ids, pools, x = z['peptide_ids'].copy(), z['pools'].copy(), z['features'].copy()
    records = pd.read_csv(PROCESSED / 'fr3_record_map.csv')
    for column in ('sequence', 'pool', 'evidence_tier', 'graphpart_fold'):
        if (records.groupby('peptide_id')[column].nunique(dropna=False) > 1).any():
            raise ValueError(f'Conflicting duplicate record IDs in {column}')
    # Accepted C1 source records repeat some sequences under the same ID;
    # the feature cache has exactly one row per unique ID/sequence.
    records = records.drop_duplicates('peptide_id').set_index('peptide_id')
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate feature IDs')
    records = records.loc[ids].reset_index()
    if not np.array_equal(records.pool.to_numpy(), pools):
        raise ValueError('Cache/record pool alignment mismatch')
    if x.shape != (len(records), 495) or not np.isfinite(x).all():
        raise ValueError('Invalid raw feature schema')
    descriptors = pd.read_parquet(PROCESSED / 'fr3_descriptor_table.parquet').set_index('peptide_id').loc[ids]
    names = json.loads((PROCESSED / 'fr3_fusion_schema.json').read_text())['feature_names'][480:]
    if not np.array_equal(records.sequence.to_numpy(), descriptors.sequence.to_numpy()):
        raise ValueError('Descriptor/cache sequence alignment mismatch')
    if not np.allclose(x[:, 480:], descriptors[names].to_numpy(), rtol=1e-6, atol=1e-6):
        raise ValueError('Descriptor/cache numeric row alignment mismatch')
    return records, x


def partition_indices(records: pd.DataFrame, fold: int):
    if fold not in range(5):
        raise ValueError('fold must be 0..4')
    retained = records.pool.eq('FR1_positives') & records.graphpart_fold.notna()
    val_fold = (fold + 1) % 5
    train = np.flatnonzero(retained & ~records.graphpart_fold.isin([fold, val_fold]))
    val = np.flatnonzero(retained & records.graphpart_fold.eq(val_fold))
    test = np.flatnonzero(retained & records.graphpart_fold.eq(fold))
    if not all(len(a) for a in (train, val, test)):
        raise ValueError('Empty GraphPart partition')
    return train, val, test


def training_scaler(x, train_indices):
    if len(train_indices) == 0:
        raise ValueError('Empty scaler fit')
    mean = x[train_indices].astype(np.float64).mean(axis=0)
    std = x[train_indices].astype(np.float64).std(axis=0)
    std[std < 1e-12] = 1.0
    return mean, std


def study_data(records, raw, config, method):
    tr, va, te = partition_indices(records, config.fold_id)
    if method == 'PN':
        tr = tr[records.iloc[tr].evidence_tier.eq('E1').to_numpy()]
        va = va[records.iloc[va].evidence_tier.eq('E1').to_numpy()]
    mean, std = training_scaler(raw, tr)
    scaled = ((raw.astype(np.float64) - mean) / std).astype(np.float32)

    def pool(name, idx):
        rows = records.iloc[idx]
        return PoolData(name, rows.peptide_id.to_numpy(), rows.sequence.to_numpy(),
                        _slice_features(scaled[idx], config.feature_representation),
                        rows.evidence_tier.fillna('').to_numpy())

    subsets = dict(train_positive=pool('train_positive', tr),
                   validation_positive=pool('validation_positive', va),
                   held_out_positive=pool('held_out_positive', te))
    for field, source in [('c1', 'C1'), ('c2', 'C2'),
                          ('c3_fold_challenges', 'C3'), ('external_control', 'external_control')]:
        idx = np.flatnonzero(records.pool.eq(source))
        if source == 'C3':
            from plantaox.c2_pu.curation.c3 import load_fold_challenges
            selected = load_fold_challenges(PROCESSED / 'c3_similarity_ranking.csv', config.fold_id)
            lookup = dict(zip(records.peptide_id, range(len(records))))
            idx = np.asarray([lookup[pid] for pid in selected.peptide_id])
        # C3 is descriptive only: no centroid/ranking fitted on inner validation
        # can affect optimization or selection in this study.
        subsets[field] = pool(field, idx)
    leakage = assert_no_cross_subset_overlap(subsets)
    data = ExperimentData(config.fold_id, config.feature_representation, config.feature_dim,
                          **subsets, leakage_report=leakage)
    scaler = dict(mean=mean.tolist(), std=std.tolist(),
                  fit_peptide_ids=records.iloc[tr].peptide_id.tolist(),
                  validation_fold=(config.fold_id + 1) % 5,
                  validation_positive_ids=records.iloc[va].peptide_id.tolist(),
                  held_out_positive_ids=records.iloc[te].peptide_id.tolist())
    return data, scaler


def positive_recovery_threshold(scores):
    """Positive-only validation heuristic; cannot estimate specificity or MCC."""
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 1 or len(scores) < 2 or not np.isfinite(scores).all():
        raise ValueError('Need at least two finite positive validation scores')
    return float(np.quantile(np.clip(scores, 0, 1), .1, method='lower'))


def add_c2_mixture(dataset, c2, mixed_validation):
    """Append disjoint unlabeled C2 rows; preserve every positive/evidence field."""
    from plantaox.c2_pu.experiment_data import split_ids_train_validation
    c2_train, c2_val = split_ids_train_validation(c2.peptide_ids.tolist(), .15, 42)
    lookup = dict(zip(c2.peptide_ids, range(len(c2.peptide_ids))))
    result = replace(dataset,
        train_unlabeled_features=np.concatenate([dataset.train_unlabeled_features, c2.features[[lookup[p] for p in c2_train]]]),
        train_unlabeled_ids=np.r_[dataset.train_unlabeled_ids, c2_train])
    if mixed_validation:
        result = replace(result,
            validation_unlabeled_features=np.concatenate([dataset.validation_unlabeled_features, c2.features[[lookup[p] for p in c2_val]]]),
            validation_unlabeled_ids=np.r_[dataset.validation_unlabeled_ids, c2_val])
    if set(result.train_unlabeled_ids) & set(result.validation_unlabeled_ids):
        raise ValueError('Mixture train/validation overlap')
    return result, dict(train_ids=c2_train, validation_ids=c2_val, validation_used=mixed_validation,
                       provisional_mixture_prior=dataset.prior,
                       native_source_counts=dict(c1_train=len(dataset.train_unlabeled_ids), c2_train=len(c2_train)))


def metrics(y, raw, threshold=.5):
    y, raw = np.asarray(y), np.asarray(raw)
    if set(np.unique(y)) != {0, 1}:
        raise ValueError('Expected explicit 0/1 labels for a two-class metric view')
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Invalid threshold')
    result = classification_metrics(y, raw, np.clip(raw, 0, 1))
    from sklearn.metrics import confusion_matrix, matthews_corrcoef, precision_score, f1_score
    pred = np.clip(raw, 0, 1) >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    result.update(threshold=float(threshold), mcc=float(matthews_corrcoef(y, pred)),
                  precision=float(precision_score(y, pred, zero_division=0)),
                  recall=float(tp / (tp + fn)), specificity=float(tn / (tn + fp)),
                  f1=float(f1_score(y, pred, zero_division=0)),
                  balanced_accuracy=float((tp / (tp + fn) + tn / (tn + fp)) / 2),
                  confusion_matrix=dict(tp=int(tp), tn=int(tn), fp=int(fp), fn=int(fn)))
    return result


def restore_predict(run_dir, config, method):
    if method in ('TwoStep', 'Bagging'):
        from plantaox.c2_pu.pu_sklearn_common import load_sklearn_checkpoint
        estimator = load_sklearn_checkpoint(run_dir / 'checkpoint_best.joblib')['estimator']
        classes = getattr(estimator, 'classes_', getattr(getattr(estimator, 'estimator', None), 'classes_', None))
        if np.asarray(classes).tolist() != [0, 1]:
            raise ValueError(f'Unexpected probability class order: {classes}')
        return lambda x: np.asarray(estimator.predict_proba(x)[:, 1], dtype=float)
    import torch
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import load_checkpoint
    model = BinaryMlp(MlpArchitecture(input_dim=config.feature_dim, hidden_dims=config.hidden_dims))
    load_checkpoint(run_dir / 'checkpoint_best.pt', model)
    model.eval()

    def predict(x):
        with torch.no_grad():
            return model.predict_proba(torch.from_numpy(x.copy())).cpu().numpy().reshape(-1).astype(float)
    return predict


def run_one(study, method, representation, fold, seed, *, prior=.1, batch=256,
            historical_recipe=False, phase='main', max_epochs=50,
            mix_c2=False, mixed_validation=False):
    from plantaox.c2_pu.pn_baseline import build_pn_dataset, train_pn_baseline
    from plantaox.c2_pu.nnpu_baseline import build_nnpu_dataset, train_nnpu_baseline
    from plantaox.c2_pu.corrective_nnpu import train_corrective_nnpu
    from plantaox.c2_pu.pu_sklearn_common import build_sklearn_pu_dataset
    from plantaox.c2_pu.two_step_pu_baseline import train_two_step_pu_baseline
    from plantaox.c2_pu.pu_bagging_baseline import train_pu_bagging_baseline
    baseline = dict(PN='PN', Direct='nnPU', Corrective='nnPU', TwoStep='TwoStepPU', Bagging='PUBagging')[method]
    run_dir = create_run_dir(RUNS / study.name, f'{phase}_{method}_{representation}_f{fold}_s{seed}_pi{prior}_b{batch}')
    config = ExperimentConfig(experiment_id=run_dir.name, baseline=baseline, fold_id=fold,
                              feature_representation=representation, train_seed=seed, eval_seed=42,
                              hidden_dims=(128, 64) if historical_recipe else (32,),
                              learning_rate=.001 if historical_recipe else .0003,
                              weight_decay=0 if historical_recipe else .001,
                              batch_size=batch, max_epochs=max_epochs, device='cpu', checkpoint_dir=str(run_dir))
    records, raw = load_raw()
    data, scaler = study_data(records, raw, config, method)
    resolved = config.to_dict() | dict(method=method, prior=prior, beta=0, gamma=1,
                                      phase=phase, historical_recipe=historical_recipe,
                                      bagging_members=25, validation_graphpart_fold=(fold + 1) % 5,
                                      threshold_policy='fixed .5 plus validation positive tenth percentile',
                                      data_versions=['pp1_baseline_v1', 'pp2_baseline_v1'],
                                      unlabeled_training='C1+C2' if mix_c2 else 'C1',
                                      unlabeled_validation='C1+C2' if mixed_validation else 'C1',
                                      training_source_sha256={str(p): sha256_of(p) for p in Path('src/plantaox/c2_pu').glob('*.py')})
    write_resolved_config(run_dir, resolved)
    write_json(run_dir / 'scaler.json', scaler)
    with RunContext(run_dir):
        started = time.perf_counter()
        if method == 'PN':
            dataset = build_pn_dataset(data, config)
            result = train_pn_baseline(config, dataset, run_dir, early_stopping_patience=8)
            vx = dataset.validation_features
            vy = dataset.validation_labels.astype(int)
            pos_mask = vy == 1
        else:
            dataset = (build_nnpu_dataset(data, config, prior=prior) if method in ('Direct', 'Corrective')
                       else build_sklearn_pu_dataset(data, config))
            if mix_c2:
                if method != 'Corrective':
                    raise ValueError('Amendment authorizes only corrective nnPU mixture follow-up')
                dataset, mixture_membership = add_c2_mixture(dataset, data.c2, mixed_validation)
                write_json(run_dir / 'c2_mixture_membership.json', mixture_membership)
            if method == 'Direct':
                result = train_nnpu_baseline(config, dataset, run_dir, early_stopping_patience=8)
            elif method == 'Corrective':
                result = train_corrective_nnpu(config, dataset, run_dir, early_stopping_patience=8)
            elif method == 'TwoStep':
                result = train_two_step_pu_baseline(config, dataset, run_dir)
            else:
                result = train_pu_bagging_baseline(config, dataset, run_dir, n_estimators=25)
            vx = np.concatenate([dataset.validation_positive_features, dataset.validation_unlabeled_features])
            vy = np.r_[np.ones(len(dataset.validation_positive_ids), dtype=int),
                       np.zeros(len(dataset.validation_unlabeled_ids), dtype=int)]
            pos_mask = vy == 1
        membership = {}
        for name in dataset.__dataclass_fields__:
            if name.endswith('_ids'):
                value = getattr(dataset, name)
                membership[name] = value.tolist() if hasattr(value, 'tolist') else value
        write_json(run_dir / 'membership.json', membership)
        predict = restore_predict(run_dir, config, method)
        scores = predict(vx)
        # Restore a second time: predictions, not serialized timestamp bytes, must match.
        if not np.array_equal(scores, restore_predict(run_dir, config, method)(vx)):
            raise RuntimeError('Checkpoint restoration changed predictions')
        threshold = positive_recovery_threshold(scores[pos_mask])
        rng = np.random.default_rng(2026)
        thresholds = [positive_recovery_threshold(rng.choice(scores[pos_mask], pos_mask.sum(), replace=True)) for _ in range(500)]
        proxy = metrics(vy, scores)
        selection = (result['best_val_loss'] if method == 'PN' else
                     result['best_val_nnpu_risk'] if method in ('Direct', 'Corrective') else
                     -proxy['average_precision'])
        checkpoint = run_dir / ('checkpoint_best.joblib' if method in ('TwoStep', 'Bagging') else 'checkpoint_best.pt')
        summary = dict(run_dir=str(run_dir), config=resolved, selection_value=selection,
                       selection_note='validation BCE / assumed-prior nnPU risk / negative proxy AP; lower is better',
                       validation_proxy=proxy, threshold=threshold,
                       threshold_bootstrap_95=np.quantile(thresholds, [.025, .975]).tolist(),
                       threshold_n_positive=int(pos_mask.sum()), training=result,
                       checkpoint_sha256=sha256_of(checkpoint), scaler_sha256=sha256_of(run_dir / 'scaler.json'),
                       runtime_seconds=time.perf_counter() - started, checkpoint_restoration_exact=True)
        write_json(run_dir / 'summary.json', summary)
    print(json.dumps(dict(run=run_dir.name, seconds=round(summary['runtime_seconds'], 2),
                          selection=round(selection, 5))), flush=True)
    return summary


def initialize():
    branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
    if branch != 'experiment/c2-mcc-improvement-v1':
        raise RuntimeError(f'Expected owner development branch; found {branch!r}')
    study = create_run_dir(REPORTS, 'study')
    write_json(study / 'preservation_before.json', inventory_snapshot())
    inventory = pd.read_csv(PROCESSED / 'C2_PP1_ARTIFACT_INVENTORY.csv')
    discrepancies = [r.path for r in inventory.itertuples() if Path(r.path).is_file() and sha256_of(Path(r.path)) != r.sha256]
    import torch, sklearn, scipy
    write_json(study / 'provenance.json', dict(branch=branch,
               git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               preexisting_inventory_discrepancies=discrepancies,
               python=platform.python_version(), torch=torch.__version__, sklearn=sklearn.__version__, scipy=scipy.__version__,
               source_sha256={str(p): sha256_of(p) for p in Path('src/plantaox/c2_pu').rglob('*.py')},
               input_sha256={str(p): sha256_of(p) for p in [INTERIM / 'fr3_fused_raw.npz', PROCESSED / 'fr3_record_map.csv',
                              REPORTS / 'EXPERIMENT_PLAN.md']},
               threads=1, cuda=False, seeds=[42, 123, 2026], external_used_for_selection=False))
    print(study, flush=True)
    return study


def train_stage(study, stage):
    ledger_path = study / 'training_ledger.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []

    def run(method, rep, fold, seed, **kw):
        phase = kw.get('phase', 'main')
        key = (method, rep, fold, seed, kw.get('prior', .1), kw.get('batch', 256), phase)
        for row in ledger:
            c = row['config']
            if key == (c['method'], c['feature_representation'], c['fold_id'], c['train_seed'], c['prior'], c['batch_size'], c['phase']):
                return row
        value = run_one(study, method, rep, fold, seed, **kw)
        ledger.append(value)
        write_json(ledger_path, ledger)
        assert_preserved(json.loads((study / 'preservation_before.json').read_text()))
        return value

    if stage == 'pilot':
        for method in METHODS:
            for rep in REPRESENTATIONS:
                run(method, rep, 0, 42)
        total = sum(r['runtime_seconds'] for r in ledger)
        write_json(study / 'compute_estimate.json', dict(pilot_seconds=total,
                   projected_main_125_fits_seconds=total / 15 * 125,
                   note='Local CPU extrapolation; actual early stopping and fit costs vary.'))
    elif stage == 'expand':
        for fold in range(5):
            for method in METHODS:
                for rep in REPRESENTATIONS:
                    run(method, rep, fold, 42)
        selections = select_representations(ledger)
        # No external predictions have been computed at this point.
        write_json(study / 'selection_frozen.json', selections)
        for selected in selections:
            for seed in (123, 2026):
                run(selected['method'], selected['representation'], selected['fold'], seed)
        for prior in (.05, .20):
            run('Corrective', 'fused', 0, 42, prior=prior, phase='sensitivity')
        run('Corrective', 'fused', 0, 42, batch=32, phase='batch_comparator')
        run('Corrective', 'fused', 0, 42, batch=32, historical_recipe=True, phase='historical_recipe')
    elif stage == 'followup':
        for fold in range(5):
            for seed in (42, 123, 2026):
                for mixed_validation in (False, True):
                    run('Corrective', 'fused', fold, seed, mix_c2=True, mixed_validation=mixed_validation,
                        phase='mixed_mixed_validation' if mixed_validation else 'mixed_c1_validation')
        for seed in (123, 2026):
            run('Corrective', 'fused', 3, seed, phase='matched_c1_fused')
    else:
        raise ValueError(stage)


def select_representations(ledger):
    """Use only persisted development selection values, never retrospective metrics."""
    selections = []
    for fold in range(5):
        for method in METHODS:
            candidates = [r for r in ledger if r['config']['phase'] == 'main' and
                          r['config']['fold_id'] == fold and r['config']['method'] == method and r['config']['train_seed'] == 42]
            reps = [r['config']['feature_representation'] for r in candidates]
            if sorted(reps) != sorted(REPRESENTATIONS):
                raise ValueError(f'Need exactly three feature candidates for fold{fold} {method}')
            if not all(np.isfinite(r['selection_value']) for r in candidates):
                raise ValueError('Nonfinite development selection criterion')
            best = min(candidates, key=lambda r: (r['selection_value'], REPRESENTATIONS.index(r['config']['feature_representation'])))
            selections.append(dict(fold=fold, method=method, representation=best['config']['feature_representation'],
                                   seed42_run_dir=best['run_dir'], selection_value=best['selection_value']))
    return selections


def reproduce_selected(study):
    """Repeat frozen fold0/seed42 fits; never select using these results."""
    selections = json.loads((study / 'selection_frozen.json').read_text())
    ledger = json.loads((study / 'training_ledger.json').read_text())
    records, raw = load_raw()
    results = []
    for selected in selections:
        if selected['fold'] != 0:
            continue
        original = next(row for row in ledger if row['run_dir'] == selected['seed42_run_dir'])
        method, rep = selected['method'], selected['representation']
        repeat = run_one(study, method, rep, 0, 42, phase='reproduction')
        config = ExperimentConfig.from_dict(original['config'])
        data, _ = study_data(records, raw, config, method)
        pools = ('train_positive', 'validation_positive', 'held_out_positive', 'c1', 'c2', 'c3_fold_challenges', 'external_control')
        x = np.concatenate([getattr(data, name).features for name in pools])
        first = restore_predict(Path(original['run_dir']), config, method)(x)
        second = restore_predict(Path(repeat['run_dir']), config, method)(x)
        results.append(dict(method=method, original_run=original['run_dir'], repeated_run=repeat['run_dir'],
                            exact_predictions=bool(np.array_equal(first, second)), max_absolute_difference=float(np.max(np.abs(first - second))),
                            n_prediction_rows=len(x), repeated_summary=repeat))
        write_json(study / 'deterministic_retraining.json', results)
    if not all(r['exact_predictions'] for r in results):
        raise RuntimeError('Deterministic retraining mismatch; inspect retained results')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['init', 'diagnose', 'pilot', 'expand', 'followup', 'evaluate', 'reproduce', 'finalize'])
    parser.add_argument('--study', type=Path)
    args = parser.parse_args()
    import torch
    from threadpoolctl import threadpool_limits
    torch.set_num_threads(1)
    with threadpool_limits(limits=1):
        if args.stage == 'init':
            initialize()
            return
        if args.study is None or not (args.study / 'preservation_before.json').exists():
            parser.error('--study must name an initialized study')
        if args.stage in ('pilot', 'expand', 'followup'):
            train_stage(args.study, args.stage)
        elif args.stage == 'reproduce':
            reproduce_selected(args.study)
        elif args.stage == 'finalize':
            from plantaox.c2_pu.mcc_study_report import finalize
            finalize(args.study)
        else:
            from plantaox.c2_pu.mcc_study_report import diagnose, evaluate
            (diagnose if args.stage == 'diagnose' else evaluate)(args.study)
        assert_preserved(json.loads((args.study / 'preservation_before.json').read_text()))


if __name__ == '__main__':
    main()
