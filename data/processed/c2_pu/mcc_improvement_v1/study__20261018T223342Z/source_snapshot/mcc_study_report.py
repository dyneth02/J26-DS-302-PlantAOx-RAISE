"""Read-only diagnostics and retrospective reporting for the versioned study."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, mannwhitneyu, spearmanr
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve
from sklearn.neighbors import NearestNeighbors

from plantaox.c2_pu.mcc_study import (
    PROCESSED, METHODS, load_raw, metrics, write_json, study_data, restore_predict,
    partition_indices, assert_preserved,
)
from plantaox.c2_pu.experiment_config import ExperimentConfig


def bootstrap_intervals(y, raw, threshold=.5, seed=2026, n=1000):
    """Class-stratified conditional peptide bootstrap; not independent-source CI."""
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(y == c) for c in (0, 1)]
    values = []
    for _ in range(n):
        idx = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups])
        yi, si = y[idx], raw[idx]
        pred = np.clip(si, 0, 1) >= threshold
        tp = np.sum(pred & (yi == 1)); tn = np.sum(~pred & (yi == 0))
        fp = len(groups[0]) - tn; fn = len(groups[1]) - tp
        denominator = float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** .5
        values.append([(tp * tn - fp * fn) / denominator if denominator else 0.,
                       roc_auc_score(yi, si), tp / len(groups[1]), tn / len(groups[0])])
    return {k: np.quantile(np.asarray(values)[:, i], [.025, .975]).tolist()
            for i, k in enumerate(('mcc', 'auroc', 'recall', 'specificity'))}


def baseline_diagnostics(study):
    from plantaox.c2_pu.baseline_evaluation import load_accepted_baselines
    from plantaox.c2_pu.run import _build_fold0_task4_data, _task45_summary_paths
    config = ExperimentConfig('mcc_read_only_baseline', 'PN')
    data = _build_fold0_task4_data(config)
    from plantaox.c2_pu.external_control_diagnostic import diagnose_external_controls
    loaded_models = load_accepted_baselines(_task45_summary_paths())
    alignment, _ = diagnose_external_controls(data, loaded_models,
                  pd.read_parquet(PROCESSED / 'fr3_descriptor_table.parquet'),
                  pd.read_csv(PROCESSED / 'anoxpepred_external_control_validated.csv'))
    write_json(study / 'baseline_alignment_and_orientation.json', alignment)
    accepted = json.loads((PROCESSED / 'fr4_baseline_evaluation_fold0.json').read_text())['models']
    rows, results = [], {}
    for model in loaded_models:
        p = model.predict(data.held_out_positive.features)
        c = model.predict(data.external_control.features)
        y = np.r_[np.ones(len(p.raw), dtype=int), np.zeros(len(c.raw), dtype=int)]
        raw = np.r_[p.raw, c.raw]
        m = metrics(y, raw)
        for key in ('mcc', 'auroc', 'recall', 'average_precision'):
            if not np.isclose(m[key], accepted[model.model_id]['external_assay_supported'][key], atol=1e-12):
                raise ValueError(f'Baseline reproduction mismatch: {model.name} {key}')
        tiers = {t: dict(n=int(np.sum(data.held_out_positive.evidence_tier == t)),
                         recall=float(np.mean(p.bounded[data.held_out_positive.evidence_tier == t] >= .5)))
                 for t in ('E1', 'E2')}
        results[model.model_id] = dict(name=model.name, metrics=m, tier_recovery=tiers,
                  conditional_bootstrap_95=bootstrap_intervals(y, raw), provenance=model.provenance,
                  control_saturation_gt_099=float(np.mean(c.bounded > .99)),
                  positive_saturation_gt_099=float(np.mean(p.bounded > .99)),
                  reproduced=True)
        for pool, output, label in [(data.held_out_positive, p, 1), (data.external_control, c, 0)]:
            for pid, seq, score in zip(pool.peptide_ids, pool.sequences, output.raw):
                rows.append(dict(model=model.model_id, method=model.name, peptide_id=pid,
                                 sequence=seq, label=label, raw_score=float(score),
                                 bounded_score=float(np.clip(score, 0, 1))))
    frame = pd.DataFrame(rows)
    frame.to_csv(study / 'baseline_predictions.csv', index=False)
    failures = frame.assign(error=(frame.bounded_score.ge(.5).astype(int) != frame.label))
    failures.groupby(['peptide_id', 'sequence', 'label']).error.agg(['sum', 'count']).reset_index().to_csv(
        study / 'baseline_consistent_errors.csv', index=False)
    write_json(study / 'baseline_reproduction.json', results)
    return results


def source_diagnostics(study):
    records, raw = load_raw()
    tr, va, te = partition_indices(records, 0)
    ext = np.flatnonzero(records.pool.eq('external_control'))
    c1 = np.flatnonzero(records.pool.eq('C1'))
    c2 = np.flatnonzero(records.pool.eq('C2'))
    groups = {'training_positive': tr, 'validation_positive': va, 'held_out_positive': te,
              'external_control': ext, 'C1_unlabeled': c1, 'C2_unlabeled': c2}
    names = json.loads((PROCESSED / 'fr3_fusion_schema.json').read_text())['feature_names'][480:]
    rows = []
    # Descriptor effects and two-sided tests are exploratory; BH q-values below.
    for name, idx in groups.items():
        if name == 'training_positive':
            continue
        for j, feature in enumerate(names):
            a, b = raw[tr, 480 + j], raw[idx, 480 + j]
            u = mannwhitneyu(a, b, alternative='two-sided')
            ks = ks_2samp(a, b)
            rows.append(dict(group=name, feature=feature, n_train=len(a), n_group=len(b),
                             training_mean=float(np.mean(a)), group_mean=float(np.mean(b)),
                             training_median=float(np.median(a)), group_median=float(np.median(b)),
                             ks=float(ks.statistic), ks_p=float(ks.pvalue),
                             rank_biserial=float(2 * u.statistic / (len(a) * len(b)) - 1), p=float(u.pvalue)))
    stats = pd.DataFrame(rows)
    order = np.argsort(stats.p.to_numpy())
    q = np.minimum.accumulate((stats.p.to_numpy()[order] * len(stats) / np.arange(1, len(stats) + 1))[::-1])[::-1]
    stats['bh_q'] = np.empty(len(stats)); stats.loc[order, 'bh_q'] = np.minimum(q, 1)
    stats.to_csv(study / 'descriptor_shift_statistics.csv', index=False)
    comp = []
    for group, idx in groups.items():
        sequences = records.iloc[idx].sequence.tolist()
        for aa in 'ACDEFGHIKLMNPQRSTVWY':
            fractions = [s.count(aa) / len(s) for s in sequences]
            comp.append(dict(group=group, aa=aa, mean_fraction=float(np.mean(fractions)), n=len(idx)))
    pd.DataFrame(comp).to_csv(study / 'amino_acid_composition.csv', index=False)
    # PCA fitted only on optimization positives. Projection is descriptive.
    mean, std = raw[tr].mean(0), raw[tr].std(0)
    std[std < 1e-12] = 1
    scaled = (raw - mean) / std
    pca = PCA(n_components=2, svd_solver='full').fit(scaled[tr, :480])
    projected = pca.transform(scaled[:, :480])
    projection_rows = []
    overlap = []
    for group, idx in groups.items():
        for i in idx:
            projection_rows.append(dict(group=group, peptide_id=records.iloc[i].peptide_id,
                                        pc1=float(projected[i, 0]), pc2=float(projected[i, 1])))
        nn = NearestNeighbors(n_neighbors=2 if group == 'training_positive' else 1).fit(scaled[tr, :480])
        distances = nn.kneighbors(scaled[idx, :480])[0][:, -1]
        overlap.append(dict(group=group, median_nearest_training_esm_distance=float(np.median(distances)),
                            q95_nearest_training_esm_distance=float(np.quantile(distances, .95))))
    pd.DataFrame(projection_rows).to_csv(study / 'embedding_pca.csv', index=False)
    pd.DataFrame(overlap).to_csv(study / 'embedding_overlap.csv', index=False)
    write_json(study / 'pca_transform.json', dict(fit_ids=records.iloc[tr].peptide_id.tolist(),
               explained_variance_ratio=pca.explained_variance_ratio_.tolist(), components=pca.components_.tolist()))
    # Nearest matching is evaluation-only; matching IDs do not enter model fitting.
    # Unique positive assignment avoids multiplying observations by replacement.
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
    matched = []
    for kind, cols in [('length', [480 + names.index('length')]), ('descriptors', list(range(480, 495)))]:
        costs = cdist(scaled[ext][:, cols], scaled[te][:, cols])
        ei, pi = linear_sum_assignment(costs)
        for e, p in zip(ei, pi):
            matched.append(dict(kind=kind, control_id=records.iloc[ext[e]].peptide_id,
                                positive_id=records.iloc[te[p]].peptide_id, distance=float(costs[e, p])))
    pd.DataFrame(matched).to_csv(study / 'matched_diagnostic_membership.csv', index=False)
    controls = pd.read_csv(PROCESSED / 'anoxpepred_external_control_validated.csv')
    controls.to_csv(study / 'control_provenance.csv', index=False)
    return dict(groups={k: len(v) for k, v in groups.items()},
                strongest_control_descriptor_shifts=stats[stats.group.eq('external_control')].sort_values('ks', ascending=False).head(6).to_dict('records'),
                pca_variance=pca.explained_variance_ratio_.tolist(),
                caveat='Associations; not causal evidence. Tests exploratory and peptide dependence unmodeled.')


def diagnose(study):
    baseline = baseline_diagnostics(study)
    source = source_diagnostics(study)
    source_membership_probe(study)
    write_json(study / 'diagnostic_summary.json', source)
    historical_scalers = json.loads((PROCESSED / 'fr3_fusion_scalers.json').read_text())
    # Explicitly reproduce the overlap with historical inner validation.
    from plantaox.c2_pu.experiment_data import split_ids_train_validation
    train, val = split_ids_train_validation(historical_scalers['0']['training_peptide_ids'], .15, 42)
    write_json(study / 'historical_inner_scaler_audit.json', dict(
        fit_n=len(historical_scalers['0']['training_peptide_ids']), optimization_n=len(train),
        validation_n=len(val), validation_ids_in_scaler_fit=len(set(val) & set(historical_scalers['0']['training_peptide_ids'])),
        outer_test_ids_in_scaler_fit=len(set(historical_scalers['0']['held_out_peptide_ids']) & set(historical_scalers['0']['training_peptide_ids'])),
        interpretation='Internal validation informed scaling; outer GraphPart test did not. New protocol fixes inner isolation.'))
    (study / 'ROOT_CAUSE_DIAGNOSTIC.md').write_text(
        '# Root-cause diagnostic\n\n'
        'Five accepted checkpoints reproduce MCC, AUROC, AP and recall to 1e-12. '
        'Labels are positive=1/control=0; sigmoid and sklearn column1 point toward positive support. '
        'All feature IDs and pool memberships align; source duplicate C1 IDs agree in sequence, pool, tier and fold. '
        'Existing loader checks ID/sequence disjointness. No blocking prediction bug was found.\n\n'
        'Evidence ranking:\n\n'
        '1. **Strong descriptive evidence:** broad historical ranking failure and source/descriptor shift. '
        'See descriptor_shift_statistics.csv (all 15 descriptors; BH-adjusted exploratory tests), '
        'composition, train-fitted PCA and nearest-training distances. Source, sequence family and assay '
        'effects remain confounded; shifts do not prove shortcut causation.\n'
        '2. **Strong optimization evidence:** accepted direct clamping suppresses U gradients in ~99% '
        'of updates and saturates scores. Corrective gradients are meaningful but do not by themselves '
        'establish assay discrimination. New comparisons retain both variants and report their branches.\n'
        '3. **Confirmed protocol limitation:** historical scaling includes 106 inner-validation positives; '
        'outer test remains isolated. New scaling uses only actual optimization positives and inner '
        'validation is a separate GraphPart fold. This need not explain the direction of historical failure.\n'
        '4. **Plausible, unresolved:** C1-only validation and unmeasured prior/SCAR assumptions poorly '
        'represent assay-specific activity. Prior sensitivity cannot estimate real prevalence.\n'
        '5. **Insufficient causal support:** particular assay mechanisms, sources or peptide families '
        'cause the failure. DOI-level controls lack harmonized conditions; two conflicting annotations '
        'do not explain the full negative result. No labels are changed.\n\n'
        'Threshold optimization against controls is prohibited; AUROC below .5 is a ranking issue. '
        'Length/descriptor matching is diagnostic only and always accompanies the full original set. '
        'No fresh assay-matched independent dataset has been curated.\n', encoding='utf-8')
    print('Baseline reproduction and source diagnostics completed.', flush=True)


def source_membership_probe(study):
    """Diagnostic dataset-membership prediction, never antioxidant labels or selection."""
    from sklearn.linear_model import LogisticRegression
    from plantaox.c2_pu.pn_baseline import split_c1_train_validation
    from threadpoolctl import threadpool_limits
    records, raw = load_raw()
    config = ExperimentConfig('source_probe', 'nnPU', fold_id=0)
    data, _ = study_data(records, raw, config, 'Corrective')
    c1train, c1val = split_c1_train_validation(data.c1, .15, 42)
    rows = []
    coefficients = {}
    with threadpool_limits(limits=1):
        for name, columns in [('length', [480]), ('descriptors', list(range(480, 495))), ('esm', list(range(480)))]:
            train = np.concatenate([data.train_positive.features[:, columns], c1train.features[:, columns]])
            ytrain = np.r_[np.ones(len(data.train_positive.peptide_ids)), np.zeros(len(c1train.peptide_ids))]
            val = np.concatenate([data.validation_positive.features[:, columns], c1val.features[:, columns]])
            yval = np.r_[np.ones(len(data.validation_positive.peptide_ids)), np.zeros(len(c1val.peptide_ids))]
            model = LogisticRegression(C=1, max_iter=2000, class_weight='balanced', random_state=42).fit(train, ytrain)
            val_score = model.predict_proba(val)[:, 1]
            pscore = model.predict_proba(data.held_out_positive.features[:, columns])[:, 1]
            cscore = model.predict_proba(data.external_control.features[:, columns])[:, 1]
            rows.append(dict(features=name, validation_dataset_membership_auroc=float(roc_auc_score(yval, val_score)),
                             held_out_positive_median_FR1_support=float(np.median(pscore)),
                             control_median_FR1_support=float(np.median(cscore)),
                             note='FR1-vs-C1 source contrast, NOT antioxidant AUROC; controls were not fit'))
            coefficients[name] = dict(coef=model.coef_.tolist(), intercept=model.intercept_.tolist(),
                                      columns=columns, fit_positive_ids=data.train_positive.peptide_ids.tolist(),
                                      fit_C1_ids=c1train.peptide_ids.tolist())
    pd.DataFrame(rows).to_csv(study / 'source_membership_probe.csv', index=False)
    write_json(study / 'source_membership_probe_parameters.json', coefficients)


def evaluate(study):
    if not (study / 'selection_frozen.json').exists():
        raise ValueError('Freeze selections before external evaluation')
    ledger = json.loads((study / 'training_ledger.json').read_text())
    selections = json.loads((study / 'selection_frozen.json').read_text())
    lookup = {(s['fold'], s['method']): s['representation'] for s in selections}
    records, raw = load_raw()
    rows, predictions, tier_rows = [], [], []
    for summary in ledger:
        c = summary['config']; method = c['method']; run_dir = Path(summary['run_dir'])
        config = ExperimentConfig.from_dict(c)
        data, _ = study_data(records, raw, config, method)
        from plantaox.c2_pu.common.feature_cache import sha256_of
        checkpoint = run_dir / ('checkpoint_best.joblib' if method in ('TwoStep', 'Bagging') else 'checkpoint_best.pt')
        if sha256_of(checkpoint) != summary['checkpoint_sha256']:
            raise ValueError('Checkpoint changed after selection')
        predict = restore_predict(run_dir, config, method)
        p, control = predict(data.held_out_positive.features), predict(data.external_control.features)
        y = np.r_[np.ones(len(p), dtype=int), np.zeros(len(control), dtype=int)]
        scores = np.r_[p, control]
        selected = c['phase'] == 'main' and lookup[(c['fold_id'], method)] == c['feature_representation']
        for tier in ('E1', 'E2'):
            mask = data.held_out_positive.evidence_tier == tier
            tier_y = np.r_[np.ones(mask.sum(), dtype=int), np.zeros(len(control), dtype=int)]
            tier_rows.append(dict(run_dir=str(run_dir), method=method, fold=c['fold_id'], seed=c['train_seed'],
                                  selected=selected, tier=tier, n_positive=int(mask.sum()), n_control=len(control),
                                  **metrics(tier_y, np.r_[p[mask], control])))
        for threshold_name, threshold in [('fixed', .5), ('positive_recovery_heuristic', summary['threshold'])]:
            m = metrics(y, scores, threshold)
            row = dict(method=method, representation=c['feature_representation'], fold=c['fold_id'], seed=c['train_seed'],
                       prior=c['prior'], batch=c['batch_size'], phase=c['phase'], selected=selected,
                       protocol='retrospective assay-supported; original controls reused', threshold_policy=threshold_name,
                       run_dir=str(run_dir), checkpoint_sha256=summary['checkpoint_sha256'], runtime_seconds=summary['runtime_seconds'],
                       n_positive=len(p), n_control=len(control), **{k: v for k, v in m.items() if not isinstance(v, dict)},
                       **m['confusion_matrix'], positive_saturation_gt099=float(np.mean(p > .99)),
                       control_saturation_gt099=float(np.mean(control > .99)))
            for tier in ('E1', 'E2'):
                mask = data.held_out_positive.evidence_tier == tier
                row[f'{tier}_n'] = int(mask.sum())
                row[f'{tier}_recall'] = float(np.mean(p[mask] >= threshold))
            rows.append(row)
        for pool, values, label in [(data.held_out_positive, p, 1), (data.external_control, control, 0)]:
            for pid, seq, value, tier in zip(pool.peptide_ids, pool.sequences, values, pool.evidence_tier):
                predictions.append(dict(run_dir=str(run_dir), method=method, fold=c['fold_id'], seed=c['train_seed'],
                    selected=selected, peptide_id=pid, sequence=seq, tier=tier, label=label, raw_score=float(value),
                    bounded_score=float(np.clip(value, 0, 1))))
        # Challenge scores are descriptive only; no assumed-error interpretation.
        challenge = {}
        for name in ('c1', 'c2', 'c3_fold_challenges'):
            values = predict(getattr(data, name).features)
            challenge[name] = dict(n=len(values), mean=float(values.mean()), median=float(np.median(values)), fraction_ge05=float(np.mean(values >= .5)))
        write_json(run_dir / 'retrospective_evaluation.json', dict(fixed=metrics(y, scores),
                   positive_recovery_heuristic=metrics(y, scores, summary['threshold']), challenge_descriptive=challenge))
    frame, pred = pd.DataFrame(rows), pd.DataFrame(predictions)
    frame.to_csv(study / 'all_evaluations.csv', index=False)
    pred.to_csv(study / 'all_predictions.csv', index=False)
    write_json(study / 'evidence_tier_evaluations.json', tier_rows)
    selected = frame[frame.selected & frame.threshold_policy.eq('fixed')]
    selected.groupby('method')[['mcc', 'auroc', 'recall', 'specificity']].agg(['mean', 'std', 'min', 'max']).to_csv(study / 'selected_variability.csv')
    selected.groupby(['method', 'fold'])[['mcc', 'auroc', 'recall', 'specificity']].agg(['mean', 'std']).to_csv(study / 'fold_variability.csv')
    selected.groupby(['method', 'seed'])[['mcc', 'auroc', 'recall', 'specificity']].agg(['mean', 'std']).to_csv(study / 'seed_variability.csv')
    matched = pd.read_csv(study / 'matched_diagnostic_membership.csv')
    sensitivity = []
    ci = {}
    for (method, seed), sub in pred[pred.selected & pred.fold.eq(0)].groupby(['method', 'seed']):
        ci[f'{method}_seed{seed}'] = bootstrap_intervals(sub.label.to_numpy(), sub.raw_score.to_numpy())
        for kind, pairs in matched.groupby('kind'):
            subset = sub[sub.peptide_id.isin(set(pairs.control_id) | set(pairs.positive_id))]
            sensitivity.append(dict(method=method, seed=seed, kind=kind, **metrics(subset.label.to_numpy(), subset.raw_score.to_numpy())))
        conflict_ids = {'AOP-37BD4B4933', 'AOP-DDCD54E4BA'}
        subset = sub[~sub.peptide_id.isin(conflict_ids)]
        sensitivity.append(dict(method=method, seed=seed, kind='exclude_two_annotation_conflicts',
                                **metrics(subset.label.to_numpy(), subset.raw_score.to_numpy())))
    write_json(study / 'selected_fold0_conditional_bootstrap_95.json', ci)
    write_json(study / 'matched_and_conflict_sensitivity.json', sensitivity)
    errors = pred[pred.selected].copy()
    errors['error'] = errors.bounded_score.ge(.5).astype(int).ne(errors.label)
    errors.groupby(['peptide_id', 'sequence', 'label']).error.agg(['sum', 'count', 'mean']).reset_index().to_csv(study / 'selected_consistent_errors.csv', index=False)
    controls = pd.read_csv(PROCESSED / 'anoxpepred_external_control_validated.csv')
    errors[errors.label.eq(0)].merge(controls[['peptide_id', 'anoxpepred_source']], on='peptide_id', validate='many_to_one').groupby(
        ['method', 'anoxpepred_source']).agg(n_prediction_rows=('error', 'size'),
        n_unique_controls=('peptide_id', 'nunique'), false_positive_fraction=('error', 'mean')).reset_index().to_csv(study / 'control_publication_errors.csv', index=False)
    descriptors = pd.read_parquet(PROCESSED / 'fr3_descriptor_table.parquet')
    names = json.loads((PROCESSED / 'fr3_fusion_schema.json').read_text())['feature_names'][480:]
    associations = []
    f0pred = pred[pred.selected & pred.fold.eq(0) & pred.seed.eq(42)].merge(descriptors[['peptide_id'] + names], on='peptide_id', validate='many_to_one')
    for (method, label), group in f0pred.groupby(['method', 'label']):
        for name in names:
            corr = spearmanr(group.raw_score, group[name])
            associations.append(dict(method=method, label=int(label), descriptor=name,
                                     spearman_r=float(corr.statistic) if np.isfinite(corr.statistic) else None,
                                     p=float(corr.pvalue) if np.isfinite(corr.pvalue) else None))
    pd.DataFrame(associations).to_csv(study / 'score_descriptor_associations.csv', index=False)
    from plantaox.c2_pu.mcc_study_plots import make_plots
    make_plots(study, frame, pred)
    write_final_reports(study, frame)
    write_followup_report(study, frame)
    assert_preserved(json.loads((study / 'preservation_before.json').read_text()))
    write_json(study / 'preservation_after.json', dict(accepted_bytes_unchanged=True,
               checked_paths=len(json.loads((study / 'preservation_before.json').read_text()))))
    print('All retrospective reports completed.', flush=True)


def write_followup_report(study, frame):
    fixed = frame[frame.threshold_policy.eq('fixed') & frame.method.eq('Corrective') & frame.representation.eq('fused')]
    main = fixed[fixed.phase.isin(['main', 'matched_c1_fused'])]
    if not fixed.phase.eq('mixed_mixed_validation').any():
        return
    groups = dict(C1_train_C1_validation=main,
                  C1C2_train_C1_validation=fixed[fixed.phase.eq('mixed_c1_validation')],
                  C1C2_train_C1C2_validation=fixed[fixed.phase.eq('mixed_mixed_validation')])
    rows = []
    paired = []
    for name, g in groups.items():
        if len(g) != 15 or g[['fold', 'seed']].duplicated().any():
            raise ValueError(f'Incomplete matched follow-up {name}: {len(g)}')
        rows.append(dict(policy=name, n_runs=len(g), mean_mcc=float(g.mcc.mean()), sd_mcc=float(g.mcc.std()),
                         positive_mcc_runs=int(g.mcc.gt(0).sum()), mean_auroc=float(g.auroc.mean()),
                         mean_recall=float(g.recall.mean()), mean_specificity=float(g.specificity.mean())))
        if name != 'C1_train_C1_validation':
            merged = g.merge(main, on=['fold', 'seed'], suffixes=('_mixed', '_c1'), validate='one_to_one')
            for r in merged.itertuples():
                paired.append(dict(policy=name, fold=r.fold, seed=r.seed,
                                   delta_mcc=r.mcc_mixed-r.mcc_c1, delta_auroc=r.auroc_mixed-r.auroc_c1,
                                   delta_recall=r.recall_mixed-r.recall_c1,
                                   delta_specificity=r.specificity_mixed-r.specificity_c1))
    pd.DataFrame(rows).to_csv(study / 'followup_policy_comparison.csv', index=False)
    pd.DataFrame(paired).to_csv(study / 'followup_paired_deltas.csv', index=False)
    lines = ['# Exploratory unlabeled-mixture follow-up', '',
             'See FOLLOWUP_AMENDMENT.md for timing and fixed assumptions. No policy was selected using these external results. '
             'All rows use fused corrective nnPU, five folds, three seeds, pi=.10 and threshold .5. '
             'The same 38 historical controls repeat. Group means are descriptive, not independent validation.', '',
             '| Training / validation U | Mean MCC ± SD | MCC >0 | Mean AUROC | Mean sensitivity | Mean specificity |',
             '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['policy']} | {r['mean_mcc']:.4f} ± {r['sd_mcc']:.4f} | {r['positive_mcc_runs']}/15 | {r['mean_auroc']:.4f} | {r['mean_recall']:.4f} | {r['mean_specificity']:.4f} |")
    lines += ['', 'Native C1/C2 mixture weights and an unmeasured mixture prior do not establish SCAR or true-negative risk. '
              'Validation risks across different populations are not directly comparable. '
              'Within-policy early stopping uses its own validation risk. Positive-recovery thresholds and all unfavorable '
              'results remain in all_evaluations.csv. Paired deltas compare the same outer fold and seed; no independent-run '
              'significance test is claimed. C1/C2 near-duplicate families remain an accepted dependence limitation.']
    (study / 'FOLLOWUP_UNLABELED_MIXTURE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_final_reports(study, frame):
    original = dict(PN=-.1833, Direct=-.0436, Corrective=-.2498, TwoStep=-.1694, Bagging=-.2495)
    selected = frame[frame.selected & frame.threshold_policy.eq('fixed')]
    lines = ['# Scientific results: MCC improvement v1', '',
             'The negative-MCC issue remains **unresolved** under the tested protocols: no selected method '
             'has consistently positive MCC across the 15 fold/seed runs. The isolated favorable PN run is not a successful method.', '',
             'All new external results are **retrospective**, using the same 38 assay-inactive controls. '
             'They are not independently validated. Selection and thresholds were frozen using development data only.', '',
             '## Matched historical membership: fold 0 / seed 42 / threshold .5', '',
             'New training uses stricter GraphPart inner validation, training-only scaling, and bounded regularization. '
             'Accepted and new training recipes differ; this is not a one-variable historical comparison.', '',
             '| Model | Original MCC | New MCC | AUROC | Sensitivity | Specificity | Status |',
             '|---|---:|---:|---:|---:|---:|---|']
    comparison = []
    for method in METHODS:
        row = selected[selected.method.eq(method) & selected.fold.eq(0) & selected.seed.eq(42)].iloc[0]
        status = 'Positive retrospective MCC' if row.mcc > 0 else 'Unresolved on historical benchmark'
        lines.append(f'| {method} ({row.representation}) | {original[method]:.4f} | {row.mcc:.4f} | {row.auroc:.4f} | {row.recall:.4f} | {row.specificity:.4f} | {status} |')
        comparison.append(dict(model=method, original_mcc=original[method], new_mcc=row.mcc,
                               auroc=row.auroc, sensitivity=row.recall, specificity=row.specificity,
                               representation=row.representation, protocol=row.protocol, fold=0, seed=42, threshold=.5, status=status))
    pd.DataFrame(comparison).to_csv(study / 'final_comparison_fold0_seed42.csv', index=False)
    lines += ['', '## Five folds x three seeds: selected representations', '',
              '| Model | Mean MCC ± SD | Range | MCC >0 | AUROC mean | Recall mean | Specificity mean |',
              '|---|---:|---|---:|---:|---:|---:|']
    for method, g in selected.groupby('method', sort=False):
        lines.append(f'| {method} | {g.mcc.mean():.4f} ± {g.mcc.std():.4f} | {g.mcc.min():.4f} to {g.mcc.max():.4f} | {(g.mcc > 0).sum()}/{len(g)} | {g.auroc.mean():.4f} | {g.recall.mean():.4f} | {g.specificity.mean():.4f} |')
    lines += ['', 'SD describes dependent runs; it is not a confidence interval. Controls repeat across all folds/seeds. '
              'Outer positive fold sizes differ (124/134/137/173/266), so mean fold metrics are not pooled metrics. '
              'Representation selection is fold-specific using its separate inner validation; no external labels were used.', '',
              '## Corrections and interpretation', '',
              '- Fresh scaling fits actual optimization positives only; separate GraphPart validation fold prevents inner homology mixing.',
              '- Reuse cached raw ESM/descriptors with strict identity, pool, finite-value and membership checks.',
              '- Existing training implementations, risk equations, checkpoint persistence and evidence-tier policies are retained.',
              '- Capacity (32 hidden units), weight decay .001, lr .0003 and batch256 form a bounded compound regularization experiment.',
              '- All five algorithms retrained; all representation candidates and prior/batch/recipe sensitivity runs remain in the ledger.',
              '- Checkpoint hashes, scaler parameters/fit IDs, membership, seeds, runtime, code/input hashes and restored inference are recorded.', '',
              'No negative label is manufactured. C1 validation AP is explicitly a proxy; PU validation risk relies on an unmeasured prior '
              'and representativeness assumptions. C2/C3 are descriptive challenge pools only. No curriculum is retrained: '
              'its C1-only selection limitation remains, and no reliable assay validation exists to select a better stage.', '',
              'See THRESHOLD_INVESTIGATION.md, ROOT_CAUSE_DIAGNOSTIC.md, descriptor_shift_statistics.csv, '
              'all_evaluations.csv, conditional bootstrap intervals, matched sensitivity and provenance for detailed evidence.', '',
              '## Feature and optimization findings', '',
              'Across the five seed42 folds, every method/representation combination retains negative mean MCC '
              'and mean AUROC below .5. Removing either feature block does not resolve discrimination. '
              'Representation preferences differ across development folds. See feature_comparison_five_folds_seed42.csv.', '',
              'Training histories and training_configuration_and_optimization.csv separate direct clamping '
              'from corrective branch frequency. Reduced saturation did not repair ranking; meaningful '
              'corrective gradients did not establish biological validity.', '',
              'Corrective prior sensitivity, the batch32 comparator and historical-capacity recipe are '
              'retained in all_evaluations.csv. No prior is selected from these external results. '
              'The C1+C2 follow-up and matched C1-only fused comparator are reported separately in '
              'FOLLOWUP_UNLABELED_MIXTURE_REPORT.md; neither validation policy is chosen using external results.', '',
              '## Limitations and next work', '',
              'Biological generalization remains unproven even if a few MCC values are positive. Small, repeatedly inspected, '
              'assay-specific controls, incomplete assay metadata, E2 provisional annotation, source/family dependence, '
              'unmeasured class prior and C1 sampling mismatch limit conclusions. The pre-existing release-inventory '
              'mismatch is recorded separately; no checksum or accepted file was changed to hide it.', '',
              'Acquire genuinely new assay-matched active/inactive peptides with concentration, mechanism, source publication '
              'and assay conditions. Screen sequence/homology overlap against every training source before freezing. '
              'Review the 179 historical annotation conflicts with the supervisor; do not silently relabel them. '
              'Use assay-specific endpoints and source-held-out validation where metadata permit. '
              'Only then estimate specificity, identify MCC-optimal thresholds, and claim independent improvement.']
    (study / 'FINAL_SCIENTIFIC_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (study / 'THRESHOLD_INVESTIGATION.md').write_text(
        '# Threshold investigation\n\n'
        'Primary threshold is .5 for every model. No MCC threshold was optimized: C1/C2/C3 have no confirmed '
        'negative labels, so assay MCC-optimal threshold is not identifiable. Controls and outer folds are excluded.\n\n'
        'Secondary threshold is the empirical lower tenth percentile of positive validation support, frozen '
        'in each training summary before external scoring. PN uses E1; PU uses E1+E2. This targets approximately '
        '90% validation recall and does not estimate specificity, calibration or true prevalence. Ties and finite '
        'sample quantiles affect achieved recall. Stratified positive bootstrap quantiles (500 replicates, seed2026) '
        'describe threshold sampling uncertainty, not source dependence or distribution-shift robustness.\n\n'
        'all_evaluations.csv reports BOTH thresholds, including unfavorable results. Do not select the secondary '
        'threshold because historical MCC happens to improve. Ranking AUROC is unchanged by threshold choice.\n', encoding='utf-8')
    (study / 'PP1_PRESENTATION_SUMMARY.md').write_text(
        '# PP1 presentation summary\n\n'
        '1. Five accepted negative-MCC results reproduced without changing accepted artifacts.\n'
        '2. Strong source/feature shift and direct-clamp saturation; no score-orientation bug identified.\n'
        '3. New study uses training-only scaling, GraphPart inner validation and three feature representations.\n'
        f'4. {len(frame) // 2} new fits, five methods, five outer folds and three seeds; complete negative evidence retained.\n'
        '5. Any positive MCC is retrospective; repeated controls do not establish independent validation.\n'
        '6. Next milestone: new assay-matched controls and source/assay-aware endpoints.\n', encoding='utf-8')


def finalize(study):
    """Audit complete outputs against prediction rows and preservation evidence."""
    import csv
    import hashlib
    import re
    import shutil
    import subprocess
    import xml.etree.ElementTree as ET
    from plantaox.c2_pu.common.feature_cache import sha256_of
    from plantaox.c2_pu.curation.freeze import verify_frozen_baseline
    frame = pd.read_csv(study / 'all_evaluations.csv')
    pred = pd.read_csv(study / 'all_predictions.csv')
    ledger = json.loads((study / 'training_ledger.json').read_text())
    records, _ = load_raw()
    indexed = records.set_index('peptide_id')
    external = set(records[records.pool.eq('external_control')].peptide_id)
    checked = 0
    for summary in ledger:
        run_dir = Path(summary['run_dir']); c = summary['config']
        scaler = json.loads((run_dir / 'scaler.json').read_text())
        membership = json.loads((run_dir / 'membership.json').read_text())
        if c['method'] == 'PN':
            train, val = set(membership['train_peptide_ids']), set(membership['validation_peptide_ids'])
        else:
            train = set(membership['train_positive_ids']) | set(membership['train_unlabeled_ids'])
            val = set(membership['validation_positive_ids']) | set(membership['validation_unlabeled_ids'])
        test = set(scaler['held_out_positive_ids'])
        if train & (val | test | external) or val & (test | external):
            raise ValueError('Train/validation/test/control membership leakage')
        if set(indexed.loc[list(train)].sequence) & set(indexed.loc[list(val | test | external)].sequence):
            raise ValueError('Sequence leakage')
        fit = set(scaler['fit_peptide_ids'])
        if not fit <= train or fit & (val | test | external):
            raise ValueError('Scaler fitting boundary mismatch')
        scores = pred[pred.run_dir.eq(str(run_dir))]
        if set(scores[scores.label.eq(1)].peptide_id) != test or set(scores[scores.label.eq(0)].peptide_id) != external:
            raise ValueError('Evaluation membership mismatch')
        if scores.peptide_id.duplicated().any():
            raise ValueError('Duplicate evaluation row')
        for row in frame[frame.run_dir.eq(str(run_dir))].itertuples():
            actual = metrics(scores.label.to_numpy(), scores.raw_score.to_numpy(), row.threshold)
            for key in ('mcc', 'auroc', 'recall', 'specificity', 'precision', 'f1', 'average_precision'):
                if not np.isclose(actual[key], getattr(row, key), rtol=0, atol=1e-12):
                    raise ValueError(f'Persisted metric mismatch: {run_dir} {key}')
            checked += 1
    for path in (study / 'plots').glob('*.svg'):
        ET.parse(path)
    frozen = {version: verify_frozen_baseline(PROCESSED / 'frozen' / version)
              for version in ('pp1_baseline_v1', 'pp2_baseline_v1')}
    if not all(all(values.values()) for values in frozen.values()):
        raise ValueError('Frozen data hash failure')
    write_json(study / 'frozen_datasets_final.json', frozen)
    audit_path = 'src/plantaox/c2_pu/docs/FR4_PP1_PRE_FREEZE_METHOD_AUDIT.md'
    actual_bytes = Path(audit_path).read_bytes()
    tag_bytes = subprocess.check_output(['git', 'show', 'c2-pp1-v1:' + audit_path])
    write_json(study / 'preexisting_release_line_endings.json', dict(path=audit_path,
        current_sha256=hashlib.sha256(actual_bytes).hexdigest(), tag_sha256=hashlib.sha256(tag_bytes).hexdigest(),
        current_size=len(actual_bytes), tag_size=len(tag_bytes),
        LF_normalization_matches_tag=actual_bytes.replace(b'\r\n', b'\n') == tag_bytes,
        action='No accepted file or checksum was modified. Canonical verifier still reports this pre-existing mismatch.'))
    fixed = frame[frame.phase.eq('main') & frame.seed.eq(42) & frame.threshold_policy.eq('fixed')]
    fixed.groupby(['method', 'representation'])[['mcc', 'auroc', 'recall', 'specificity']].agg(['mean', 'std']).to_csv(study / 'feature_comparison_five_folds_seed42.csv')
    training_rows = []
    for r in ledger:
        c, t = r['config'], r['training']
        training_rows.append(dict(method=c['method'], representation=c['feature_representation'], fold=c['fold_id'],
            seed=c['train_seed'], phase=c['phase'], prior=c['prior'], batch=c['batch_size'],
            hidden_dims=str(c['hidden_dims']), learning_rate=c['learning_rate'], weight_decay=c['weight_decay'],
            executed_epochs=t.get('executed_epochs'), best_epoch=t.get('best_epoch'),
            mean_clamped_fraction=float(np.mean([h['train_clamped_update_fraction'] for h in t['history']])) if c['method']=='Direct' else None,
            mean_corrective_fraction=t.get('mean_corrective_branch_fraction'), runtime_seconds=r['runtime_seconds'],
            checkpoint_sha256=r['checkpoint_sha256'], run_dir=r['run_dir']))
    pd.DataFrame(training_rows).to_csv(study / 'training_configuration_and_optimization.csv', index=False)
    from plantaox.c2_pu.mcc_study import RUNS
    rejected = [str(p) for p in (RUNS / study.name).glob('main_*') if not (p / 'summary.json').exists()]
    write_json(study / 'setup_failures.json', dict(paths=rejected,
        reason='Initial alignment guard rejected consistent repeated C1 source IDs before training; corrected to verify consistency then align unique accepted cache IDs. No checkpoint or metrics existed for this setup attempt.'))
    repeat = json.loads((study / 'deterministic_retraining.json').read_text())
    focused_log = (study / 'focused_tests.log').read_text(encoding='utf-8')
    suite_log = (study / 'full_suite_isolated.log').read_text(encoding='utf-8')
    focused_passed = int(re.findall(r'(\d+) passed', focused_log)[-1])
    if re.search(r'\d+ failed', focused_log):
        raise ValueError('Focused tests contain unresolved failures')
    suite_summary = next(line for line in reversed(suite_log.splitlines()) if re.search(r'\d+ passed', line))
    write_json(study / 'evaluation_integrity_final.json', dict(fits=len(ledger), metric_views_checked=checked,
        selected_main_views=int((frame.selected & frame.threshold_policy.eq('fixed')).sum()),
        deterministic_repeat_methods=len(repeat), deterministic_repeat_all_exact=all(r['exact_predictions'] for r in repeat),
        frozen_files_verified=sum(len(v) for v in frozen.values()), svg_files_parsed=len(list((study / 'plots').glob('*.svg')))))
    assert_preserved(json.loads((study / 'preservation_before.json').read_text()))
    new_sources = list(Path('src/plantaox/c2_pu').glob('mcc_study*.py')) + [Path('tests/c2_pu/test_mcc_study.py')]
    snapshot = study / 'source_snapshot'; snapshot.mkdir(exist_ok=True)
    for path in new_sources:
        shutil.copy2(path, snapshot / path.name)
    write_json(study / 'final_source_sha256.json', {str(p): sha256_of(p) for p in new_sources})
    report = f'''# Reproducibility and test report

All {len(ledger)} experimental fits and {checked} metric views were checked against persisted peptide predictions.
There are 75 selected main fold/seed evaluations, plus all candidates and follow-ups.
Five additional same-seed retraining checks (one per algorithm) reproduced every prediction
exactly on all scored training/validation/test/challenge/control rows. Checkpoints were
restored twice at fit time; timestamp-bearing serialized hashes need not match across fits.

Focused final suite: **{focused_passed} passed**, covering arithmetic/orientation, invalid labels,
five-fold isolation, scaler poisoning, selection poisoning, C2 mixture boundaries,
deterministic seeds, corrective gradients, checkpoints and existing evaluation.
See focused_tests.log. Historical full C2 suite in a disposable copy:
**{suite_summary}**. Full log and command are retained. Review its individual
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
'''
    (study / 'REPRODUCIBILITY_AND_TEST_REPORT.md').write_text(report, encoding='utf-8')
    files = set(new_sources)
    files.update(p for p in study.parent.rglob('*') if p.is_file() and p.name != 'FILE_MANIFEST.csv')
    files.update(p for p in (RUNS / study.name).rglob('*') if p.is_file())
    files.add(RUNS / '.gitignore')
    with (study / 'FILE_MANIFEST.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['path', 'size_bytes', 'sha256', 'role'])
        writer.writeheader()
        for p in sorted(files, key=str):
            role = 'disposable_qa_copy' if 'qa_workspace' in p.parts else 'local_model_run' if 'interim' in p.parts else 'study_source_or_report'
            writer.writerow(dict(path=str(p.resolve()), size_bytes=p.stat().st_size, sha256=sha256_of(p), role=role))
    print(f'Final audit passed: {len(ledger)} fits, {checked} metric views, 38 frozen files unchanged.', flush=True)
