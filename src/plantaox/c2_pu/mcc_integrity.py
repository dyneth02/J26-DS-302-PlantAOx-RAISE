"""Fail-closed replay and preservation contracts for future C2 experiments.

These checks do not retroactively certify or modify existing v1 results.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def frozen_json(path,value):
    """Never replace a frozen value; an identical retry leaves its bytes alone."""
    path=Path(path)
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=json.loads(json.dumps(value)):
            raise ValueError(f'Frozen selection/execution identity differs: {path}; initialize a new study')
        return
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def require_new_outputs(folder,names):
    existing=[str(Path(folder)/name) for name in names if (Path(folder)/name).exists()]
    if existing: raise FileExistsError(f'Preserved study outputs already exist: {existing}; use a new versioned audit/study directory')


def verify_saved_scaler(path,expected_hash,raw,fit_indices,fit_ids):
    path=Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_hash:
        raise ValueError('Saved scaler SHA-256 mismatch')
    scaler=json.loads(path.read_text(encoding='utf-8'))
    if scaler.get('fit_peptide_ids')!=list(fit_ids):raise ValueError('Saved scaler fit membership mismatch')
    mean=np.asarray(scaler['mean'],dtype=float);std=np.asarray(scaler['std'],dtype=float)
    if mean.shape!=(raw.shape[1],) or std.shape!=mean.shape or not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std<=0):
        raise ValueError('Invalid saved scaler parameters')
    actual=raw[fit_indices].astype(np.float64)
    reference_mean=actual.mean(0);reference_std=actual.std(0);reference_std[reference_std<1e-12]=1
    if not np.array_equal(mean,reference_mean) or not np.array_equal(std,reference_std):
        raise ValueError('Saved scaler parameters do not match optimization-only data')
    return scaler


def execution_identity(config,input_hashes,source_hashes):
    # Run paths/timestamps do not change training. Every effective scientific
    # parameter and byte identity does; fail closed on absent legacy identities.
    effective={k:v for k,v in config.items() if k not in ('experiment_id','checkpoint_dir','training_source_sha256','execution_identity')}
    return dict(config=effective,input_sha256=dict(input_hashes),source_sha256=dict(source_hashes))


def require_resume_identity(stored,expected):
    actual=stored.get('execution_identity')
    if actual is None or canonical_digest(actual)!=canonical_digest(expected):
        raise ValueError('Completed fit has missing or incompatible execution identity; initialize a new study')


def evaluation_coverage(ledger,predictions,evaluations):
    runs=[r['run_dir'] for r in ledger]
    if len(runs)!=len(set(runs)):raise ValueError('Duplicate ledger run')
    expected=set(runs)
    if set(predictions.run_dir)!=expected or set(evaluations.run_dir)!=expected:
        raise ValueError('Missing or extra evaluation/prediction run')
    if predictions.duplicated(['run_dir','peptide_id']).any():raise ValueError('Duplicate prediction identity')
    if evaluations.duplicated(['run_dir','threshold_policy']).any():raise ValueError('Duplicate metric view')
    for _,g in evaluations.groupby('run_dir'):
        if set(g.threshold_policy)!= {'fixed','positive_recovery_heuristic'} or len(g)!=2:
            raise ValueError('Exactly two declared threshold views required per fit')


def run_outcomes(run_root):
    outcomes=[]
    for run in sorted(Path(run_root).iterdir()):
        if not run.is_dir() or run.name=='qa_workspace':continue
        manifest=run/'run_manifest.json';summary=run/'summary.json'
        data=json.loads(manifest.read_text()) if manifest.exists() else {}
        outcomes.append(dict(run_dir=str(run),status=data.get('status','setup_incomplete_unrecorded'),
                             summary_exists=summary.exists(),
                             reason=data.get('exception_message','No recorded exception; do not infer a cause' if not summary.exists() else None)))
    return outcomes
