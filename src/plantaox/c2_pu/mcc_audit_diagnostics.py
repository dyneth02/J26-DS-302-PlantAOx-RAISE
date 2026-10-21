"""Training-free source, length, and uncertainty diagnostics for independent audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import rankdata, pearsonr, t as student_t, ks_2samp, mannwhitneyu

from plantaox.c2_pu.mcc_audit import BASE, independent_raw, independent_metrics, split_ids, save


def partial_rank(x,y,covariates):
    """Partial Spearman via least-squares residual ranks; association only."""
    x=rankdata(x);y=rankdata(y)
    z=np.column_stack([np.ones(len(x))]+[rankdata(covariates[:,i]) for i in range(covariates.shape[1])])
    rx=x-z@np.linalg.lstsq(z,x,rcond=None)[0];ry=y-z@np.linalg.lstsq(z,y,rcond=None)[0]
    if np.linalg.norm(rx)<1e-9 or np.linalg.norm(ry)<1e-9:return None,None,int(np.linalg.matrix_rank(z))
    r=float(np.clip(np.dot(rx,ry)/np.linalg.norm(rx)/np.linalg.norm(ry),-1,1))
    rank=int(np.linalg.matrix_rank(z));df=len(x)-rank-1
    p=float(2*student_t.sf(abs(r)*np.sqrt(df/max(1-r*r,1e-16)),df)) if df>0 else None
    return r,p,rank


def wilson(success,n):
    if not n:return [None,None]
    z=1.95996398454;p=success/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(mid-half),float(mid+half)]


def bh(values):
    values=np.asarray(values);order=np.argsort(values)
    adjusted=np.minimum.accumulate((values[order]*len(values)/np.arange(1,len(values)+1))[::-1])[::-1]
    result=np.empty(len(values));result[order]=np.minimum(adjusted,1);return result


def run(study,output):
    records,raw,names=independent_raw();descriptor_names=names[480:]
    predictions=pd.read_csv(study/'all_predictions.csv')
    selected=predictions[predictions.selected]
    focal=selected[selected.fold.eq(0)&selected.seed.eq(42)]
    descriptor_frame=pd.DataFrame(raw[:,480:],columns=descriptor_names,index=records.index)
    focal=focal.merge(descriptor_frame,left_on='peptide_id',right_index=True,validate='many_to_one')
    correlations=[]
    for method,g in focal.groupby('method'):
        for name,sub in [('positive',g[g.label.eq(1)]),('E1_positive',g[g.tier.eq('E1')]),
                         ('E2_positive',g[g.tier.eq('E2')]),('assay_control',g[g.label.eq(0)])]:
            for adjustment,exclude in [('all_other_descriptors',{'length'}),('without_MW',{'length','molecular_weight'})]:
                covariate_names=[n for n in descriptor_names if n not in exclude]
                cov=sub[covariate_names].to_numpy();x=sub.length.to_numpy();y=sub.raw_score.to_numpy()
                r,p,rank=partial_rank(x,y,cov)
                rng=np.random.default_rng(4172);boot=[]
                for _ in range(500):
                    idx=rng.integers(0,len(sub),len(sub));value,_,_=partial_rank(x[idx],y[idx],cov[idx])
                    if value is not None:boot.append(value)
                correlations.append(dict(method=method,group=name,adjustment=adjustment,n=len(sub),
                    partial_spearman=r,p=p,design_rank=rank,bootstrap_valid=len(boot),
                    ci_low=float(np.quantile(boot,.025)) if boot else None,ci_high=float(np.quantile(boot,.975)) if boot else None,
                    limitations='Exploratory, correlated/derived descriptors; peptide bootstrap ignores source/family dependence'))
    corr=pd.DataFrame(correlations);finite=corr.p.notna();corr.loc[finite,'bh_q']=bh(corr.loc[finite,'p'])
    corr.to_csv(output/'length_conditional_associations.csv',index=False)
    rows=[]
    indexed=records
    for (method,fold,seed),g in selected.groupby(['method','fold','seed']):
        lengths=indexed.loc[g.peptide_id].sequence.str.len().to_numpy()
        for stratum,mask in [('2_4',lengths<=4),('5_9',(lengths>=5)&(lengths<=9)),
                             ('10_30',(lengths>=10)&(lengths<=30)),('over30',lengths>30)]:
            sub=g.iloc[np.flatnonzero(mask)];n_p=int(sub.label.eq(1).sum());n_c=int(sub.label.eq(0).sum())
            tp=int((sub.label.eq(1)&sub.bounded_score.ge(.5)).sum());tn=int((sub.label.eq(0)&sub.bounded_score.lt(.5)).sum())
            row=dict(method=method,fold=fold,seed=seed,stratum=stratum,n_positive=n_p,n_control=n_c,
                     tp=tp,tn=tn,fp=n_c-tn,fn=n_p-tp,recall=tp/n_p if n_p else None,specificity=tn/n_c if n_c else None,
                     recall_ci95=wilson(tp,n_p),specificity_ci95=wilson(tn,n_c),
                     status='two_classes' if n_p and n_c else 'MCC_AUROC_undefined_one_or_zero_classes')
            if n_p and n_c: row.update(independent_metrics(sub.label.to_numpy(),sub.raw_score.to_numpy()))
            rows.append(row)
    save(output/'length_stratified_results.json',rows)
    pd.DataFrame(rows).drop(columns=['recall_ci95','specificity_ci95']).to_csv(output/'length_stratified_results.csv',index=False)
    # Bootstrap the actual control publication, not 15 copies of each peptide.
    controls=pd.read_csv(BASE/'anoxpepred_external_control_validated.csv')
    publication=controls.set_index('peptide_id').anoxpepred_source
    interval_rows=[];existing=json.loads((study/'selected_fold0_conditional_bootstrap_95.json').read_text())
    for method,g in focal.groupby('method'):
        g=g.reset_index(drop=True);pids=np.flatnonzero(g.label.eq(1));cids=np.flatnonzero(g.label.eq(0))
        pubgroups={p:g.index[g.peptide_id.map(publication).eq(p)].to_numpy() for p in publication.unique()}
        rng=np.random.default_rng(2026);conditional=[]
        for _ in range(1000):
            idx=np.r_[rng.choice(cids,len(cids),replace=True),rng.choice(pids,len(pids),replace=True)]
            value=independent_metrics(g.iloc[idx].label.to_numpy(),g.iloc[idx].raw_score.to_numpy())
            conditional.append([value[k] for k in ('mcc','auroc','recall','specificity')])
        endpoints=np.quantile(conditional,[.025,.975],axis=0)
        for j,k in enumerate(('mcc','auroc','recall','specificity')):
            np.testing.assert_allclose(endpoints[:,j],existing[f'{method}_seed42'][k],rtol=0,atol=2e-14)
        rng=np.random.default_rng(2027);cluster=[];pubkeys=list(pubgroups)
        for _ in range(1000):
            chosen=rng.choice(pubkeys,len(pubkeys),replace=True)
            idx=np.r_[rng.choice(pids,len(pids),replace=True),np.concatenate([pubgroups[k] for k in chosen])]
            value=independent_metrics(g.iloc[idx].label.to_numpy(),g.iloc[idx].raw_score.to_numpy())
            cluster.append([value[k] for k in ('mcc','auroc','recall','specificity')])
        interval_rows.append(dict(method=method,n_control_publications=len(pubkeys),n_positive=len(pids),n_control=len(cids),
            original_peptide_intervals_reproduced=True,publication_cluster_percentile95={k:np.quantile(np.asarray(cluster)[:,j],[.025,.975]).tolist() for j,k in enumerate(('mcc','auroc','recall','specificity'))},
            caveat='Positive peptides resampled individually; only observed 11 control publications clustered. Not complete biological/family uncertainty.'))
    save(output/'publication_cluster_uncertainty.json',interval_rows)
    # Independently apply the saved source probes; no new fitting.
    tr=np.flatnonzero(records.graphpart_fold.isin([2,3,4]));va=records.index[records.graphpart_fold.eq(1)].tolist()
    mean=raw[tr].astype(float).mean(0);std=raw[tr].astype(float).std(0);std[std<1e-12]=1
    scaled=((raw.astype(float)-mean)/std).astype(np.float32)
    positions=dict(zip(records.index,range(len(records))));_,c1val=split_ids(records[records.pool.eq('C1')].index.tolist())
    val_ids=va+c1val;y=np.r_[np.ones(len(va)),np.zeros(len(c1val))]
    parameters=json.loads((study/'source_membership_probe_parameters.json').read_text());source_rows=[]
    from sklearn.metrics import roc_auc_score
    for name,p in parameters.items():
        x=scaled[[positions[k] for k in val_ids]][:,p['columns']]
        logits=x@np.asarray(p['coef'],dtype=np.float32).T+np.asarray(p['intercept'],dtype=np.float32)
        score=expit(logits).reshape(-1)
        auc=float(roc_auc_score(y,score))
        recorded=pd.read_csv(study/'source_membership_probe.csv').set_index('features').loc[name,'validation_dataset_membership_auroc']
        assert abs(auc-recorded)<1e-12
        source_rows.append(dict(representation=name,validation_source_auroc=auc,recorded=recorded,absolute_difference=abs(auc-recorded),n_positive=len(va),n_C1=len(c1val)))
    pd.DataFrame(source_rows).to_csv(output/'source_probe_verification.csv',index=False)
    # Descriptors and amino-acid composition: all stored comparisons.
    groups={'validation_positive':np.flatnonzero(records.graphpart_fold.eq(1)),
            'held_out_positive':np.flatnonzero(records.graphpart_fold.eq(0)),
            'external_control':np.flatnonzero(records.pool.eq('external_control')),
            'C1_unlabeled':np.flatnonzero(records.pool.eq('C1')),'C2_unlabeled':np.flatnonzero(records.pool.eq('C2'))}
    stored=pd.read_csv(study/'descriptor_shift_statistics.csv');deltas=[]
    for row in stored.itertuples():
        j=480+descriptor_names.index(row.feature);a=raw[tr,j];b=raw[groups[row.group],j]
        ks=ks_2samp(a,b);u=mannwhitneyu(a,b,alternative='two-sided')
        actual={'ks':ks.statistic,'ks_p':ks.pvalue,'p':u.pvalue,'rank_biserial':2*u.statistic/(len(a)*len(b))-1}
        error=max(abs(value-getattr(row,key)) for key,value in actual.items());assert error<1e-12
        deltas.append(dict(group=row.group,feature=row.feature,max_absolute_difference=error))
    pd.DataFrame(deltas).to_csv(output/'descriptor_statistics_verification.csv',index=False)
    composition=pd.read_csv(study/'amino_acid_composition.csv');groups['training_positive']=tr
    for row in composition.itertuples():
        seq=records.iloc[groups[row.group]].sequence
        actual=float(np.mean([s.count(row.aa)/len(s) for s in seq]));assert abs(actual-row.mean_fraction)<1e-14
    # Stratification/publication error outputs derive from unique controls per run.
    pub=focal[focal.label.eq(0)].merge(controls[['peptide_id','anoxpepred_source']],on='peptide_id')
    pub['error']=pub.bounded_score.ge(.5)
    pub.groupby(['method','anoxpepred_source']).agg(n_controls=('peptide_id','size'),false_positive_fraction=('error','mean')).reset_index().to_csv(output/'control_publication_errors_fold0_seed42.csv',index=False)
    save(output/'diagnostic_checks.json',dict(conditional_associations=len(corr),length_stratum_views=len(rows),
        descriptor_comparisons_verified=len(deltas),amino_acid_comparisons_verified=len(composition),
        source_probes_verified=len(source_rows),new_training=False,control_publications=controls.anoxpepred_source.nunique()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.study,args.output)
