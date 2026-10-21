"""Independent evaluation arithmetic and actual GraphPart isolation regressions."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.mcc_study import (
    assert_preserved, load_raw, metrics, partition_indices, positive_recovery_threshold,
    study_data, training_scaler, write_json,
    select_representations, METHODS, REPRESENTATIONS,
    add_c2_mixture,
)


def test_confusion_mcc_and_positive_orientation():
    y = np.array([1, 1, 1, 0, 0, 0, 0])
    s = np.array([.8, .7, .1, .9, .4, .3, .2])
    result = metrics(y, s)
    # TP2 TN3 FP1 FN1; independently calculated MCC numerator and denominator.
    assert result['confusion_matrix'] == dict(tp=2, tn=3, fp=1, fn=1)
    assert result['mcc'] == pytest.approx(5 / 12)
    assert result['specificity'] == .75
    assert result['recall'] == pytest.approx(2 / 3)
    assert metrics(y, 1 - s)['auroc'] == pytest.approx(1 - result['auroc'])


@pytest.mark.parametrize('labels', [[-1, 1], [0, 2], [1, 1]])
def test_reject_invalid_label_semantics(labels):
    with pytest.raises(ValueError):
        metrics(np.array(labels), np.array([.1, .9]))


@pytest.mark.parametrize('value', [np.nan, np.inf, -.1, 1.1])
def test_threshold_range(value):
    with pytest.raises(ValueError):
        metrics(np.array([0, 1]), np.array([.1, .9]), value)


def test_raw_two_step_scores_used_for_ranking_and_clipped_only_for_decisions():
    m = metrics(np.array([0, 1, 0, 1]), np.array([1.1, 1.2, .1, .9]))
    assert m['auroc'] == .75
    assert m['confusion_matrix'] == dict(tp=2, tn=1, fp=1, fn=0)


def test_training_scaler_does_not_fit_validation_or_controls():
    x = np.array([[1., 2], [3., 2], [100., -99], [-100., 999]])
    mean, std = training_scaler(x, [0, 1])
    poisoned = x.copy(); poisoned[2:] *= 100000
    mean2, std2 = training_scaler(poisoned, [0, 1])
    np.testing.assert_array_equal(mean, [2, 2])
    np.testing.assert_array_equal(std, [1, 1])
    np.testing.assert_array_equal(mean, mean2)
    np.testing.assert_array_equal(std, std2)


def test_positive_threshold_heuristic_and_ties():
    values = np.arange(11) / 10
    assert positive_recovery_threshold(values) == .1
    assert positive_recovery_threshold(np.ones(20) * .6) == .6
    for invalid in [[], [.4], [.1, np.nan]]:
        with pytest.raises(ValueError):
            positive_recovery_threshold(invalid)


def test_preservation_guard_detects_changes(tmp_path):
    path = tmp_path / 'accepted.txt'; path.write_text('accepted')
    from plantaox.c2_pu.common.feature_cache import sha256_of
    before = {str(path): sha256_of(path)}
    assert_preserved(before)
    path.write_text('different')
    with pytest.raises(RuntimeError, match='Accepted artifact bytes changed'):
        assert_preserved(before)


@pytest.fixture(scope='module')
def actual_raw():
    if not Path('data/interim/c2_pu/fr3_fused_raw.npz').exists():
        pytest.skip('Local accepted feature cache unavailable')
    return load_raw()


@pytest.mark.parametrize('fold', range(5))
@pytest.mark.parametrize('method', ['PN', 'Corrective'])
def test_actual_graphpart_and_scaling_boundaries(actual_raw, fold, method):
    records, raw = actual_raw
    config = ExperimentConfig('test_study', 'PN' if method == 'PN' else 'nnPU', fold_id=fold)
    data, scaler = study_data(records, raw, config, method)
    fitted = set(scaler['fit_peptide_ids'])
    va, te = set(data.validation_positive.peptide_ids), set(data.held_out_positive.peptide_ids)
    assert fitted.isdisjoint(va | te | set(data.external_control.peptide_ids))
    indexed = records.set_index('peptide_id')
    assert set(indexed.loc[list(fitted)].graphpart_fold) == set(range(5)) - {fold, (fold + 1) % 5}
    assert set(indexed.loc[list(va)].graphpart_fold) == {(fold + 1) % 5}
    assert set(indexed.loc[list(te)].graphpart_fold) == {fold}
    assert len(data.c3_fold_challenges.peptide_ids) == 2000
    assert len(data.external_control.peptide_ids) == 38
    assert data.leakage_report['overlap_found'] is False
    assert set(data.train_positive.evidence_tier) == ({'E1'} if method == 'PN' else {'E1', 'E2'})
    np.testing.assert_allclose(data.train_positive.features.mean(0), 0, atol=3e-6)
    # Poison every non-fit raw row: scaler and optimization features must be identical.
    modified = raw.copy()
    modified[~records.peptide_id.isin(fitted).to_numpy()] += 10000
    data2, scaler2 = study_data(records, modified, config, method)
    assert scaler == scaler2
    np.testing.assert_array_equal(data.train_positive.features, data2.train_positive.features)


def test_cache_rows_are_unique_and_sequences_consistent(actual_raw):
    records, raw = actual_raw
    assert len(records) == 9356
    assert records.peptide_id.is_unique
    assert records.sequence.is_unique
    assert records.pool.value_counts()['C1'] == 3788
    assert raw.shape == (9356, 495)


def test_all_outer_folds_cover_only_retained_positives(actual_raw):
    records, _ = actual_raw
    tests = [set(partition_indices(records, f)[2]) for f in range(5)]
    assert list(map(len, tests)) == [124, 134, 137, 173, 266]
    assert sum(map(len, tests)) == len(set.union(*tests)) == 834
    assert all(records.iloc[list(s)].pool.eq('FR1_positives').all() for s in tests)


def test_selection_ignores_external_metric_poisoning_and_requires_complete_candidates():
    ledger = [dict(config=dict(phase='main', fold_id=f, method=m, train_seed=42, feature_representation=r),
                   selection_value={'descriptors': .2, 'esm': .1, 'fused': .3}[r],
                   run_dir=f'{f}/{m}/{r}', external_mcc=1 if r == 'fused' else -1)
              for f in range(5) for m in METHODS for r in REPRESENTATIONS]
    chosen = select_representations(ledger)
    assert len(chosen) == 25
    assert all(s['representation'] == 'esm' for s in chosen)
    for row in ledger:
        row['external_mcc'] *= -1
    assert chosen == select_representations(ledger)
    with pytest.raises(ValueError, match='exactly three'):
        select_representations(ledger[:-1])


@pytest.mark.parametrize('mixed_validation', [False, True])
def test_c2_mixture_preserves_positive_labels_and_all_boundaries(actual_raw, mixed_validation):
    from plantaox.c2_pu.nnpu_baseline import build_nnpu_dataset
    records, raw = actual_raw
    config = ExperimentConfig('test_mixture', 'nnPU')
    data, _ = study_data(records, raw, config, 'Corrective')
    initial = build_nnpu_dataset(data, config, prior=.1)
    mixed, membership = add_c2_mixture(initial, data.c2, mixed_validation)
    assert len(membership['train_ids']) == 1700
    assert len(membership['validation_ids']) == 300
    assert set(membership['train_ids']).isdisjoint(membership['validation_ids'])
    assert len(mixed.train_unlabeled_ids) == 4920
    assert len(mixed.validation_unlabeled_ids) == (868 if mixed_validation else 568)
    np.testing.assert_array_equal(mixed.train_positive_features, initial.train_positive_features)
    np.testing.assert_array_equal(mixed.train_positive_tiers, initial.train_positive_tiers)
    assert mixed.prior == initial.prior == .1
    assert set(mixed.train_unlabeled_ids).isdisjoint(set(mixed.validation_unlabeled_ids) |
             set(data.external_control.peptide_ids) | set(data.held_out_positive.peptide_ids))
