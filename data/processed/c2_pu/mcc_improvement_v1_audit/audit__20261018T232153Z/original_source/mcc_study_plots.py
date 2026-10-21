"""Scientific figures generated from persisted study tables, never model selection."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd


def make_plots(study, frame, predictions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve, precision_recall_curve

    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.dpi': 120, 'savefig.dpi': 170, 'svg.hashsalt': 'mcc_improvement_v1'})
    folder = study / 'plots'; folder.mkdir(exist_ok=True)
    selected = frame[frame.selected & frame.threshold_policy.eq('fixed')]
    f0 = selected[selected.fold.eq(0) & selected.seed.eq(42)]
    methods = ['PN', 'Direct', 'Corrective', 'TwoStep', 'Bagging']
    palette = dict(zip(methods, ['#276190', '#bb5934', '#407849', '#885da7', '#b58c25']))

    def save(fig, name):
        fig.savefig(folder / (name + '.svg'), bbox_inches='tight')
        fig.savefig(folder / (name + '.png'), bbox_inches='tight')
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    original = [-.1833, -.0436, -.2498, -.1694, -.2495]
    positions = np.arange(5)
    ax.bar(positions - .18, original, .36, label='Accepted fold0 seed42', color='#a1a8b0')
    ax.bar(positions + .18, [f0[f0.method.eq(m)].mcc.iloc[0] for m in methods], .36,
           label='Selected new fold0 seed42', color=[palette[m] for m in methods])
    ax.axhline(0, color='black', linewidth=.7); ax.set_xticks(positions, methods)
    ax.set_ylabel('MCC at threshold 0.5')
    ax.set_title('Same historical 124 positives + 38 controls; retrospective')
    ax.legend(loc='best'); save(fig, 'mcc_original_vs_new_fold0')

    fig, ax = plt.subplots(figsize=(9, 5))
    for j, method in enumerate(methods):
        g = selected[selected.method.eq(method)]
        ax.scatter(j + (g.seed.map({42: -.15, 123: 0, 2026: .15})), g.mcc,
                   c=g.fold, cmap='viridis', vmin=0, vmax=4, s=35, alpha=.8)
        ax.plot([j - .3, j + .3], [g.mcc.mean()] * 2, color='black', linewidth=2)
    ax.set_xticks(range(5), methods); ax.axhline(0, color='gray', linewidth=.7)
    ax.set_ylabel('MCC at threshold 0.5'); ax.set_title('5 positive test folds x 3 seeds; same 38 controls reused')
    ax.text(.01, .02, 'Color: fold 0 (purple) to 4 (yellow). Black: mean. Runs are dependent.', transform=ax.transAxes, fontsize=9)
    save(fig, 'mcc_folds_seeds')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for method in methods:
        p = predictions[predictions.selected & predictions.fold.eq(0) & predictions.seed.eq(42) & predictions.method.eq(method)]
        fpr, tpr, _ = roc_curve(p.label, p.raw_score)
        precision, recall, _ = precision_recall_curve(p.label, p.raw_score)
        axes[0].plot(fpr, tpr, label=method, color=palette[method])
        axes[1].plot(recall, precision, label=method, color=palette[method])
    axes[0].plot([0, 1], [0, 1], '--', color='gray'); axes[0].set(xlabel='False positive rate', ylabel='Sensitivity', title='ROC')
    axes[1].axhline(124/162, linestyle='--', color='gray', label='Positive prevalence')
    axes[1].set(xlabel='Recall', ylabel='Precision', title='Precision-recall (raw ranking scores)')
    for ax in axes:
        ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    axes[1].legend(fontsize=8, loc='lower left')
    fig.suptitle('Selected fold0 seed42; historical assay-supported comparison')
    fig.tight_layout(); save(fig, 'roc_precision_recall_fold0')

    fig, axes = plt.subplots(1, 5, figsize=(15, 3.2))
    for ax, method in zip(axes, methods):
        p = predictions[predictions.selected & predictions.fold.eq(0) & predictions.seed.eq(42) & predictions.method.eq(method)]
        for label, name, color in [(1, 'Known positives', '#276190'), (0, 'Inactive controls', '#bb5934')]:
            values = p[p.label.eq(label)].bounded_score
            ax.hist(values, bins=np.linspace(0, 1, 16), density=True, alpha=.5, label=name, color=color)
        ax.axvline(.5, color='black', linestyle='--', linewidth=.8)
        ax.set(title=method, xlabel='Bounded score', xlim=(0, 1))
    axes[0].set_ylabel('Density'); axes[-1].legend(fontsize=7)
    fig.suptitle('Prediction support; fold0 seed42; scores are not calibrated probabilities')
    fig.tight_layout(); save(fig, 'score_distributions_fold0')

    fig, axes = plt.subplots(1, 5, figsize=(14, 3.2))
    for ax, method in zip(axes, methods):
        r = f0[f0.method.eq(method)].iloc[0]
        matrix = np.array([[r.tn, r.fp], [r.fn, r.tp]], dtype=int)
        ax.imshow(matrix, cmap='Blues', vmin=0, vmax=124)
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(j, i, str(value), ha='center', va='center', color='white' if value > 70 else 'black')
        ax.set_xticks([0, 1], ['0', '1']); ax.set_yticks([0, 1], ['0', '1'])
        ax.set(title=method, xlabel='Predicted class')
    axes[0].set_ylabel('Assay-supported label')
    fig.suptitle('Confusion matrices; fold0 seed42; fixed threshold .5')
    fig.tight_layout(); save(fig, 'confusion_matrices_fold0')

    projection = pd.read_csv(study / 'embedding_pca.csv')
    fig, ax = plt.subplots(figsize=(8, 5))
    for group, g in projection.groupby('group'):
        ax.scatter(g.pc1, g.pc2, s=10 if 'unlabeled' in group else 28, alpha=.25 if 'unlabeled' in group else .8, label=group)
    ax.set(xlabel='PC1', ylabel='PC2', title='ESM PCA fitted on fold0 optimization positives only')
    ax.legend(fontsize=8); save(fig, 'source_embedding_pca')

    descriptors = pd.read_csv(study / 'descriptor_shift_statistics.csv')
    d = descriptors[descriptors.group.eq('external_control')].sort_values('ks')
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(d.feature, d.ks, color='#276190'); ax.set(xlabel='Two-sample KS distance', title='Control vs optimization-positive descriptor shift')
    fig.tight_layout(); save(fig, 'source_descriptor_shift')

    candidates = frame[frame.phase.eq('main') & frame.seed.eq(42) & frame.threshold_policy.eq('fixed')]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for rep, color in zip(['descriptors', 'esm', 'fused'], ['#bb5934', '#276190', '#407849']):
        g = candidates[candidates.representation.eq(rep)]
        means = g.groupby('method').mcc.mean().reindex(methods)
        auc = g.groupby('method').auroc.mean().reindex(methods)
        axes[0].plot(methods, means, 'o-', label=rep, color=color)
        axes[1].plot(methods, auc, 'o-', label=rep, color=color)
    axes[0].axhline(0, color='gray', linewidth=.7); axes[1].axhline(.5, color='gray', linewidth=.7)
    axes[0].set_ylabel('Mean fold MCC'); axes[1].set_ylabel('Mean fold AUROC')
    axes[1].legend(); fig.suptitle('Feature ablations: all candidates shown; retrospective, seed42')
    fig.tight_layout(); save(fig, 'feature_representation_comparison')

    thresholds = frame[frame.selected]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for label, marker in [('fixed', 'o'), ('positive_recovery_heuristic', '^')]:
        g = thresholds[thresholds.threshold_policy.eq(label)].groupby('method')[['recall', 'specificity']].mean()
        for method in methods:
            ax.scatter(g.loc[method, 'specificity'], g.loc[method, 'recall'], color=palette[method], marker=marker, s=60)
            ax.annotate(method + (' .5' if label == 'fixed' else ' q10'), (g.loc[method, 'specificity'], g.loc[method, 'recall']), fontsize=8, xytext=(4, 3), textcoords='offset points')
    ax.set(xlabel='Retrospective mean specificity', ylabel='Mean sensitivity', xlim=(-.02, 1.02), ylim=(-.02, 1.02),
           title='Threshold policies frozen before scoring; no MCC optimization')
    save(fig, 'threshold_policy_comparison')
