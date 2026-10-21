"""Independent, read-only v1 audit. Never calls a trainer or writes to v1.

Usage: python -m plantaox.c2_pu.mcc_audit --study <v1 study> [--output <new dir>]
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import subprocess

import numpy as np
import pandas as pd

BASE = Path('data/processed/c2_pu')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False, default=str)
        stream.write('\n')


def independent_metrics(y, scores, threshold=.5):
    y, scores = np.asarray(y), np.asarray(scores, dtype=float)
    if y.ndim != 1 or scores.shape != y.shape or set(np.unique(y)) != {0, 1}:
        raise ValueError('Exactly two 0/1 classes, aligned 1D arrays required')
    if not np.isfinite(scores).all() or not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Invalid finite score/threshold contract')
    bounded = np.clip(scores, 0, 1)
    predicted = bounded >= threshold
    tp = int(np.sum(predicted & (y == 1))); tn = int(np.sum(~predicted & (y == 0)))
    fp = int(np.sum(predicted & (y == 0))); fn = int(np.sum(~predicted & (y == 1)))
    denominator = math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    pos, ctrl = scores[y == 1], scores[y == 0]
    auc = np.mean((pos[:, None] > ctrl).astype(float) + .5 * (pos[:, None] == ctrl))
    order = np.argsort(-scores, kind='stable')
    sy, ss = y[order], scores[order]
    ends = np.r_[np.flatnonzero(ss[:-1] != ss[1:]), len(ss)-1]
    cumulative = np.cumsum(sy)[ends]
    ap = np.sum(np.diff(np.r_[0, cumulative]) / len(pos) * cumulative / (ends+1))
    recall, specificity = tp/(tp+fn), tn/(tn+fp)
    return dict(tp=tp, tn=tn, fp=fp, fn=fn, mcc=(tp*tn-fp*fn)/denominator if denominator else 0.,
                auroc=float(auc), average_precision=float(ap), recall=recall, specificity=specificity,
                precision=tp/(tp+fp) if tp+fp else 0., f1=2*tp/(2*tp+fp+fn),
                balanced_accuracy=(recall+specificity)/2, brier_score_bounded=float(np.mean((bounded-y)**2)))


def split_ids(ids, fraction=.15):
    ids = sorted(ids); random.Random(42).shuffle(ids)
    count = max(1, round(len(ids)*fraction))
    return ids[count:], ids[:count]


def frozen_inputs(study):
    paths = {p for p in study.parent.rglob('*') if p.is_file()}
    runs = Path('data/interim/c2_pu/mcc_improvement_v1') / study.name
    paths.update(p for p in runs.rglob('*') if p.is_file())
    inventory = pd.read_csv(BASE / 'C2_PP1_ARTIFACT_INVENTORY.csv')
    paths.update(Path(p) for p in inventory.path)
    paths.update(Path('src/plantaox/c2_pu').glob('mcc_study*.py'))
    paths.add(Path('tests/c2_pu/test_mcc_study.py'))
    return {str(p): digest(p) if p.is_file() else None for p in sorted(paths, key=str)}


def independent_raw():
    with np.load('data/interim/c2_pu/fr3_fused_raw.npz', allow_pickle=False) as z:
        ids, pools, raw = z['peptide_ids'], z['pools'], z['features']
    records = pd.read_csv(BASE / 'fr3_record_map.csv')
    for column in ('sequence', 'pool', 'evidence_tier', 'graphpart_fold'):
        assert records.groupby('peptide_id')[column].nunique(dropna=False).max() == 1
    records = records.drop_duplicates('peptide_id').set_index('peptide_id').loc[ids]
    assert np.array_equal(records.pool.to_numpy(), pools)
    assert records.index.is_unique and records.sequence.is_unique
    splits = pd.read_csv(BASE / 'frozen/pp1_baseline_v1/graphpart_splits.csv').set_index('AC')['cluster'].dropna()
    mapped = records[records.graphpart_fold.notna()].graphpart_fold
    assert len(mapped) == 834 and mapped.to_dict() == splits.to_dict()
    descriptors = pd.read_parquet(BASE / 'fr3_descriptor_table.parquet').set_index('peptide_id').loc[ids]
    names = json.loads((BASE / 'fr3_fusion_schema.json').read_text())['feature_names']
    assert np.array_equal(descriptors.sequence, records.sequence)
    np.testing.assert_allclose(raw[:,480:], descriptors[names[480:]].to_numpy(), rtol=1e-6, atol=1e-6)
    return records, raw, names


def predict_saved(checkpoint, config):
    """Direct checkpoint restoration; independent of v1 restore_predict."""
    if checkpoint.suffix == '.joblib':
        import joblib
        payload = joblib.load(checkpoint); model = payload['estimator']
        classes = getattr(model, 'classes_', getattr(getattr(model, 'estimator', None), 'classes_', None))
        assert np.asarray(classes).tolist() == [0, 1]
        return lambda x: np.asarray(model.predict_proba(x)[:, 1], dtype=float), payload
    import torch
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    payload = torch.load(checkpoint, map_location='cpu', weights_only=False)
    architecture = payload['architecture']
    assert architecture['input_dim'] == config['feature_dim']
    assert architecture['hidden_dims'] == config['hidden_dims']
    model = BinaryMlp(MlpArchitecture.from_dict(architecture))
    model.load_state_dict(payload['state_dict'], strict=True); model.eval()
    def predict(x):
        with torch.no_grad():
            return torch.sigmoid(model(torch.from_numpy(x.copy()))).numpy().reshape(-1).astype(float)
    return predict, payload


def verify_baseline(study, output):
    provenance = json.loads((BASE / 'fr4_baseline_model_provenance.json').read_text())['models']
    accepted = json.loads((BASE / 'fr4_baseline_evaluation_fold0.json').read_text())['models']
    recorded = pd.read_csv(study / 'baseline_predictions.csv')
    scalers = json.loads((BASE / 'fr3_fusion_scalers.json').read_text())['0']
    cache_entry = json.loads((BASE / 'fr3_feature_cache_manifest.json').read_text())['folds']['0']
    assert digest(cache_entry['cache_path']) == cache_entry['cache_sha256']
    with np.load(cache_entry['cache_path']) as z:
        features, ids = z['features'], z['peptide_ids']
    lookup = {pid:i for i,pid in enumerate(ids)}
    rows = []
    for model in provenance:
        checkpoint = Path(model['checkpoint_path'])
        assert digest(checkpoint) == model['checkpoint_sha256']
        config_path = checkpoint.parent/'resolved_config.json'
        config = json.loads(config_path.read_text())
        predict, _ = predict_saved(checkpoint, config)
        scores = recorded[recorded.model.eq(model['model_id'])]
        assert set(scores[scores.label.eq(1)].peptide_id) == set(scalers['held_out_peptide_ids'])
        # Match accepted inference batch boundaries. Combining P/control rows
        # changes float32 matrix-kernel rounding by up to one ULP on this CPU.
        values = np.empty(len(scores), dtype=float)
        for label in (1, 0):
            mask = scores.label.eq(label).to_numpy()
            values[mask] = predict(features[[lookup[p] for p in scores.loc[mask,'peptide_id']]])
        np.testing.assert_allclose(values, scores.raw_score, rtol=0, atol=2e-14)
        result = independent_metrics(scores.label.to_numpy(), values)
        reference = accepted[model['model_id']]['external_assay_supported']
        deltas = {k:abs(result[k]-reference[k]) for k in ('mcc','auroc','average_precision','recall','precision','f1','balanced_accuracy','brier_score_bounded')}
        # Record every discrepancy instead of disguising historical numerical
        # differences as an exact match. Classification/ranking must agree.
        assert max(v for k,v in deltas.items() if k!='brier_score_bounded') < 1e-12
        assert {k:result[k] for k in ('tp','tn','fp','fn')} == reference['confusion_matrix']
        rows.append(dict(model=model['model'], checkpoint=str(checkpoint), sha256=digest(checkpoint),
                         max_reference_difference=max(deltas.values()),
                         original_brier=reference['brier_score_bounded'],
                         brier_absolute_difference=deltas['brier_score_bounded'], **result))
    pd.DataFrame(rows).to_csv(output/'baseline_independent_reproduction.csv', index=False)


def audit_runs(study, output):
    records, raw, names = independent_raw()
    positions = dict(zip(records.index, range(len(records))))
    external = set(records[records.pool.eq('external_control')].index)
    ledger = json.loads((study/'training_ledger.json').read_text())
    selections = json.loads((study/'selection_frozen.json').read_text())
    selected_lookup = {(s['fold'],s['method']):s['representation'] for s in selections}
    predictions = pd.read_csv(study/'all_predictions.csv')
    evaluations = pd.read_csv(study/'all_evaluations.csv')
    assert len(ledger)==len({s['run_dir'] for s in ledger})==161
    assert set(predictions.run_dir)==set(evaluations.run_dir)=={s['run_dir'] for s in ledger}
    assert not evaluations.duplicated(['run_dir','threshold_policy']).any()
    assert len(evaluations)==2*len(ledger)
    c1train,c1val=split_ids(records[records.pool.eq('C1')].index.tolist())
    c2train,c2val=split_ids(records[records.pool.eq('C2')].index.tolist())
    checks, metrics_rows, selection_checks, chronology = [], [], [], []
    for i, summary in enumerate(ledger):
        config=summary['config']; method=config['method']; fold=config['fold_id']; run=Path(summary['run_dir'])
        assert json.loads((run/'resolved_config.json').read_text())==config
        assert json.loads((run/'summary.json').read_text())==summary
        manifest=json.loads((run/'run_manifest.json').read_text()); assert manifest['status']=='completed'
        scaler_path=run/'scaler.json'; assert digest(scaler_path)==summary['scaler_sha256']
        scaler=json.loads(scaler_path.read_text()); membership=json.loads((run/'membership.json').read_text())
        train_mask=records.graphpart_fold.notna() & ~records.graphpart_fold.isin([fold,(fold+1)%5])
        val_mask=records.graphpart_fold.eq((fold+1)%5)
        if method=='PN':
            train_mask &= records.evidence_tier.eq('E1'); val_mask &= records.evidence_tier.eq('E1')
        train_p=records.index[train_mask].tolist(); val_p=records.index[val_mask].tolist()
        test=records.index[records.graphpart_fold.eq(fold)].tolist()
        assert scaler['fit_peptide_ids']==train_p and scaler['validation_positive_ids']==val_p and scaler['held_out_positive_ids']==test
        assert scaler['validation_fold']==(fold+1)%5
        train_raw=raw[[positions[p] for p in train_p]].astype(np.float64)
        mean=train_raw.mean(0); std=train_raw.std(0); std[std<1e-12]=1
        np.testing.assert_array_equal(mean,scaler['mean']); np.testing.assert_array_equal(std,scaler['std'])
        scaled=((raw.astype(float)-np.asarray(scaler['mean']))/np.asarray(scaler['std'])).astype(np.float32)
        cols={'descriptors':slice(480,495),'esm':slice(0,480),'fused':slice(0,495)}[config['feature_representation']]
        def x(ids): return scaled[[positions[p] for p in ids],cols]
        mixed=config['phase'].startswith('mixed_'); mixed_val=config['phase']=='mixed_mixed_validation'
        train_u=c1train+(c2train if mixed else []); val_u=c1val+(c2val if mixed_val else [])
        if method=='PN':
            assert membership['train_peptide_ids']==train_p+c1train
            assert membership['validation_peptide_ids']==val_p+c1val
        else:
            assert membership['train_positive_ids']==train_p and membership['validation_positive_ids']==val_p
            assert membership['train_unlabeled_ids']==train_u and membership['validation_unlabeled_ids']==val_u
        assert not (set(train_p+train_u)&set(val_p+val_u+test+list(external)))
        assert not (set(records.loc[train_p+train_u].sequence)&set(records.loc[val_p+val_u+test+list(external)].sequence))
        checkpoint=run/('checkpoint_best.joblib' if method in ('TwoStep','Bagging') else 'checkpoint_best.pt')
        assert digest(checkpoint)==summary['checkpoint_sha256']
        predict,payload=predict_saved(checkpoint,config)
        saved=predictions[predictions.run_dir.eq(str(run))]
        assert not saved.peptide_id.duplicated().any()
        assert set(saved[saved.label.eq(1)].peptide_id)==set(test)
        assert set(saved[saved.label.eq(0)].peptide_id)==external
        assert saved.sequence.tolist()==records.loc[saved.peptide_id].sequence.tolist()
        assert saved.label.tolist()==[1 if p in test else 0 for p in saved.peptide_id]
        score=np.empty(len(saved),dtype=float)
        for label in (1,0):
            mask=saved.label.eq(label).to_numpy()
            score[mask]=predict(x(saved.loc[mask,'peptide_id'].tolist()))
        prediction_difference=float(np.max(np.abs(score-saved.raw_score.to_numpy())))
        np.testing.assert_allclose(score,saved.raw_score,rtol=0,atol=2e-14)
        np.testing.assert_allclose(np.clip(score,0,1),saved.bounded_score,rtol=0,atol=2e-14)
        val_scores=predict(x(val_p+val_u)); vy=np.r_[np.ones(len(val_p)),np.zeros(len(val_u))]
        threshold=float(np.quantile(np.clip(val_scores[:len(val_p)],0,1),.1,method='lower'))
        assert abs(threshold-summary['threshold'])<1e-14
        proxy=independent_metrics(vy,val_scores)
        for key in ('mcc','auroc','average_precision','recall','specificity'):
            assert abs(proxy[key]-summary['validation_proxy'][key])<1e-12
        if method in ('PN','Direct','Corrective'):
            history=summary['training']['history']; key='val_bce_loss' if method=='PN' else 'val_nnpu_risk'
            best=float('inf'); best_epoch=None; stale=0
            for h in history:
                improved=h[key]<best-1e-4
                assert h['is_best']==improved
                if improved: best,best_epoch,stale=h[key],h['epoch'],0
                else: stale+=1
                if h is not history[-1]: assert stale<8
            assert best_epoch==payload['epoch']==summary['training']['best_epoch']
            import torch
            p_logit=torch.logit(torch.tensor(val_scores[:len(val_p)],dtype=torch.float32))
            # Recompute directly from model logits to avoid inverse-sigmoid rounding.
            from plantaox.c2_pu.models import BinaryMlp,MlpArchitecture
            model=BinaryMlp(MlpArchitecture.from_dict(payload['architecture']));model.load_state_dict(payload['state_dict']);model.eval()
            with torch.no_grad():
                if method=='PN':
                    pos_weight=torch.tensor([len(train_u)/len(train_p)],dtype=torch.float32)
                    val_loss=torch.nn.functional.binary_cross_entropy_with_logits(model(torch.from_numpy(x(val_p+val_u))),torch.tensor(vy,dtype=torch.float32).reshape(-1,1),pos_weight=pos_weight).item()
                else:
                    p_logits=model(torch.from_numpy(x(val_p))); u_logits=model(torch.from_numpy(x(val_u)))
                    pplus=torch.nn.functional.softplus(-p_logits).mean(); pminus=torch.nn.functional.softplus(p_logits).mean(); uminus=torch.nn.functional.softplus(u_logits).mean()
                    val_loss=(config['prior']*pplus+torch.clamp(uminus-config['prior']*pminus,min=0)).item()
            assert abs(val_loss-best)<2e-6
            selection=best
            assert len(history)<=config['max_epochs'] and (len(history)==config['max_epochs'] or stale==8)
            last=torch.load(run/'checkpoint_last.pt',map_location='cpu',weights_only=False)
            assert last['epoch']==len(history)-1
            logs=[json.loads(line) for line in (run/'epoch_metrics.jsonl').read_text().splitlines()]
            assert len(logs)==len(history)
            for h,l in zip(history,logs): assert all(l[k]==v for k,v in h.items())
        else:
            selection=-proxy['average_precision']
            if method=='Bagging': assert len(payload['estimator'].estimators_)==25
        assert abs(selection-summary['selection_value'])<1e-12
        expected_selected=config['phase']=='main' and selected_lookup[(fold,method)]==config['feature_representation']
        assert saved.selected.eq(expected_selected).all()
        for row in evaluations[evaluations.run_dir.eq(str(run))].itertuples():
            assert row.selected==expected_selected
            assert abs(row.threshold-(.5 if row.threshold_policy=='fixed' else threshold))<1e-14
            value=independent_metrics(saved.label.to_numpy(),score,row.threshold)
            differences={k:abs(value[k]-getattr(row,k)) for k in value}
            assert max(differences.values())<1e-12
            metrics_rows.append(dict(run_dir=str(run),method=method,fold=fold,seed=config['train_seed'],representation=config['feature_representation'],phase=config['phase'],selected=expected_selected,threshold_policy=row.threshold_policy,threshold=row.threshold,max_original_difference=max(differences.values()),**value))
        checks.append(dict(run_dir=str(run),method=method,fold=fold,seed=config['train_seed'],phase=config['phase'],
                           checkpoint_sha256=digest(checkpoint),scaler_sha256=digest(scaler_path),checkpoint_saved_at=payload['saved_at'],
                           n_train_positive=len(train_p),n_train_unlabeled=len(train_u),n_val_positive=len(val_p),n_val_unlabeled=len(val_u),
                           prediction_max_abs_difference=prediction_difference,selection_value_recomputed=selection,
                           source_hash_recorded='training_source_sha256' in config))
        chronology.append(dict(run_dir=str(run),checkpoint_saved_at=payload['saved_at'],completed_at=manifest['updated_at'],
                               selection_file_mtime=datetime.fromtimestamp((study/'selection_frozen.json').stat().st_mtime,timezone.utc).isoformat(),
                               external_score_file_mtime=datetime.fromtimestamp((run/'retrospective_evaluation.json').stat().st_mtime,timezone.utc).isoformat()))
        if (i+1)%25==0: print(f'Independently checked {i+1}/{len(ledger)} checkpoints and validation objectives',flush=True)
    for selection in selections:
        candidates=[r for r in ledger if r['config']['phase']=='main' and r['config']['fold_id']==selection['fold'] and r['config']['method']==selection['method'] and r['config']['train_seed']==42]
        best=min(candidates,key=lambda r:(r['selection_value'],('descriptors','esm','fused').index(r['config']['feature_representation'])))
        assert best['run_dir']==selection['seed42_run_dir']
        selection_checks.append(selection)
    pd.DataFrame(checks).to_csv(output/'checkpoint_scaler_membership_audit.csv',index=False)
    pd.DataFrame(metrics_rows).to_csv(output/'independent_all_metrics.csv',index=False)
    pd.DataFrame(chronology).to_csv(output/'chronology_evidence.csv',index=False)
    save(output/'selection_reconstruction.json',selection_checks)
    save(output/'fit_accounting.json',dict(ledger_total=len(ledger),phases=dict(Counter(r['config']['phase'] for r in ledger)),
        reproduction_checks=json.loads((study/'deterministic_retraining.json').read_text()),
        setup_only=json.loads((study/'setup_failures.json').read_text()),
        missing_per_run_source_hash_count=sum('training_source_sha256' not in r['config'] for r in ledger)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args(); study=args.study
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    if branch!='experiment/c2-mcc-improvement-v1': raise RuntimeError('Wrong development branch')
    output=args.output or BASE/'mcc_improvement_v1_audit'/('audit__'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True,exist_ok=False)
    print(output,flush=True)
    before=frozen_inputs(study);save(output/'preservation_before.json',before)
    import torch,sklearn,scipy
    torch.set_num_threads(1)
    save(output/'audit_environment.json',dict(branch=branch,commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        git_status=subprocess.check_output(['git','status','--short'],text=True),python=platform.python_version(),torch=torch.__version__,
        sklearn=sklearn.__version__,scipy=scipy.__version__,study=str(study),training_performed=False,
        source_sha256=digest(Path(__file__))))
    from threadpoolctl import threadpool_limits
    try:
        with threadpool_limits(limits=1):
            verify_baseline(study,output)
            audit_runs(study,output)
    except BaseException as error:
        save(output/'verification_failure.json',dict(type=type(error).__name__,message=str(error)))
        raise
    finally:
        after={p:digest(p) if Path(p).is_file() else None for p in before}
        changes=[p for p in before if before[p]!=after[p]]
        save(output/'preservation_after.json',dict(changed=changes,checked=len(before)))
        if changes: raise RuntimeError(f'Preservation failed: {changes}')
    print('Independent verification completed without modifying study inputs.',flush=True)


if __name__=='__main__': main()
