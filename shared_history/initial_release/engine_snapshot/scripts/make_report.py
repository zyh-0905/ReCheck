#!/usr/bin/env python3
"""Derive tables, descriptive intervals and vector figures from executed CSVs.

No policy is changed here. ReCheck resamples base RNG seeds jointly across all
regimes/prices. RepairLens resamples instances within the six fixed families.
"""
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.common.stats import paired_interval,zero_failure_upper

NAMES={'never':'Never','fresh':'Fresh','ttl':'Tuned TTL','entropy':'Mismatch threshold',
       'random':'Random','myopic':'Myopic','recheck':'ReCheck','no_task':'No task weights',
       'restart':'Restart','conservative':'Conservative','point_estimate':'Point estimate',
       'graph_entropy':'Graph entropy','class_entropy':'Class entropy','ec2':'EC2-style',
       'lookahead2':'RepairLens-2','exact':'Exact reference','discard_replay':'Discard replay'}

def recheck_seed_table(frame,metric):
    """Collapse all common-random-number configurations into 64 independent seeds."""
    return frame.groupby(['seed','method'])[metric].mean().unstack('method').sort_index()

def stratified_difference(a,b,groups,repeats=3000,seed=8675309):
    a=np.asarray(a,float);b=np.asarray(b,float);g=np.asarray(groups)
    if a.ndim!=1 or a.shape!=b.shape or a.shape!=g.shape or not np.isfinite(a-b).all():
        raise ValueError('finite, paired vectors with one stratum per observation required')
    rng=np.random.default_rng(seed);parts=[];values=[]
    for label in np.unique(g):
        d=(a-b)[g==label]
        if len(d)<2:raise ValueError('each stratum needs at least two instances')
        parts.append(d[rng.integers(0,len(d),size=(repeats,len(d)))].mean(1))
        values.append(d.mean())
    samples=np.mean(parts,axis=0);lo,hi=np.quantile(samples,[.025,.975])
    return {'n_clusters':len(a),'strata':len(parts),'mean_difference':float(np.mean(values)),
            'low':float(lo),'high':float(hi),'bootstrap_repeats':repeats,
            'bootstrap_seed':seed,'interval':'paired within-family percentile bootstrap; equal stratum weights; descriptive'}

def savefig(fig,name):
    fig.tight_layout(pad=.6)
    fig.savefig(ROOT/'figures'/f'{name}.pdf',bbox_inches='tight')
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=180,bbox_inches='tight')
    plt.close(fig)

def macro(name,value):return '\\newcommand{\\'+name+'}{'+value+'}\n'

def main():
    plt.rcParams.update({'font.size':10,'axes.labelsize':10,'legend.fontsize':10,
                         'xtick.labelsize':10,'ytick.labelsize':10,'pdf.fonttype':42,'ps.fonttype':42})
    r=pd.read_csv(ROOT/'results/recheck_main.csv');s=pd.read_csv(ROOT/'results/recheck_sql.csv')
    b=pd.read_csv(ROOT/'results/recheck_boundaries.csv');p=pd.read_csv(ROOT/'results/repairlens_main.csv')
    q=pd.read_csv(ROOT/'results/repairlens_support_stress.csv')
    rm=r.groupby('method').mean(numeric_only=True);pm=p.groupby('method').mean(numeric_only=True)
    sm=s.groupby('method').mean(numeric_only=True)
    claims={'scope':'controlled finite-model studies; no LLM/public benchmark/natural-failure experiment',
            'recheck':{'runs':len(r),'task_method_evaluations':int(r['tasks'].sum()),'independent_seed_clusters':int(r.seed.nunique()),
                       'means':rm[['success','task_loss','probes_per_task','objective','cpu_ms']].to_dict('index'),'comparisons':{}},
            'repairlens':{'runs':len(p),'instances':int(p.seed.nunique()),'means':pm[['complete','normalized_cost','cost','probes','planning_ms','execution_ms']].to_dict('index'),'comparisons':{}},
            'sql':{'runs':len(s),'tasks':len(s)*40,'means':sm.to_dict('index')},
            'boundaries':b.groupby(['condition','method'])[['objective','success']].mean().reset_index().to_dict('records'),
            'support_stress':q.groupby('condition')[['complete','normalized_cost','fallback']].mean().to_dict('index')}
    for metric in ['objective','success','probes_per_task']:
        wide=recheck_seed_table(r,metric)
        for base in ['myopic','ttl','entropy','fresh','no_task']:
            claims['recheck']['comparisons'][f'{metric}:recheck-{base}']=paired_interval(wide.recheck,wide[base])
    for metric in ['objective','success']:
        wide=s.pivot(index='seed',columns='method',values=metric)
        for base in ['fresh','myopic']:
            claims['sql'][f'{metric}:recheck-{base}']=paired_interval(wide.recheck,wide[base])
    for metric in ['normalized_cost','complete']:
        wide=p.pivot(index='seed',columns='method',values=metric).sort_index()
        fam=p.drop_duplicates('seed').set_index('seed').loc[wide.index,'family'].to_numpy()
        for method,base in [('exact','restart'),('lookahead2','restart'),('exact','myopic'),('exact','class_entropy'),('lookahead2','class_entropy'),('exact','discard_replay'),('lookahead2','exact')]:
            claims['repairlens']['comparisons'][f'{metric}:{method}-{base}']=stratified_difference(wide[method],wide[base],fam)
    claims['repairlens']['zero_of_120_conditional_iid_upper95']=zero_failure_upper(120)
    claims['repairlens']['mean_total_runtime_ms']=(pm.planning_ms+pm.execution_ms).to_dict()
    # Sensitivity only: assigned operation units are scaled by a hypothetical ms/unit.
    # Actual measured runtime already includes local execution. No simulated cloud
    # latency is reported as a measurement or folded into the main CPU comparison.
    be={}
    for method in ['exact','lookahead2','myopic','class_entropy']:
        saving=pm.loc['restart','cost']-pm.loc[method,'cost']
        be[method]=float(pm.loc[method,'planning_ms']/saving) if saving>0 else None
    claims['repairlens']['modeled_break_even_ms_per_declared_cost_unit']=be
    files=['recheck_main.csv','recheck_sql.csv','recheck_boundaries.csv','repairlens_main.csv','repairlens_support_stress.csv']
    claims['input_sha256']={f:hashlib.sha256((ROOT/'results'/f).read_bytes()).hexdigest() for f in files}
    (ROOT/'results/analysis.json').write_text(json.dumps(claims,indent=2))
    rm.to_csv(ROOT/'results/recheck_summary.csv');pm.to_csv(ROOT/'results/repairlens_summary.csv')
    p.groupby(['family','method'])[['normalized_cost','complete','planning_ms','execution_ms','probes']].mean().to_csv(ROOT/'results/repairlens_by_family.csv')
    lines=['\\begin{tabular}{lrrrr}','\\toprule','Policy & Success (\\%) & Loss & Probes & $J$ \\\\','\\midrule']
    for a in ['never','fresh','ttl','entropy','random','myopic','no_task','recheck']:
        x=rm.loc[a];lines.append(f"{NAMES[a]} & {100*x.success:.2f} & {x.task_loss:.4f} & {x.probes_per_task:.3f} & {x.objective:.4f} \\\\")
    lines+=['\\bottomrule','\\end{tabular}']
    (ROOT/'papers/recheck/table_main.tex').write_text('\n'.join(lines))
    lines=['\\begin{tabular}{lrrr}','\\toprule','Policy & Success (\\%) & Probes & $J$ \\\\','\\midrule']
    for a in ['never','fresh','myopic','recheck']:
        x=sm.loc[a];lines.append(f"{NAMES[a]} & {100*x.success:.2f} & {x.probes_per_task:.3f} & {x.objective:.4f} \\\\")
    lines+=['\\bottomrule','\\end{tabular}']
    (ROOT/'papers/recheck/table_sql.tex').write_text('\n'.join(lines))
    tex=macro('RCObjective',f'{rm.loc["recheck","objective"]:.4f}')
    tex+=macro('RCSuccess',f'{100*rm.loc["recheck","success"]:.2f}')
    tex+=macro('RCReductionMyopic',f'{100*(1-rm.loc["recheck","objective"]/rm.loc["myopic","objective"]):.1f}')
    tex+=macro('RCReductionTTL',f'{100*(1-rm.loc["recheck","objective"]/rm.loc["ttl","objective"]):.1f}')
    for bas,n in [('myopic','Myopic'),('ttl','TTL'),('entropy','Entropy')]:
        ci=claims['recheck']['comparisons'][f'objective:recheck-{bas}']
        tex+=macro('RCDiff'+n,f'{ci["mean_difference"]:.4f}')+macro('RCLow'+n,f'{ci["low"]:.4f}')+macro('RCHigh'+n,f'{ci["high"]:.4f}')
    (ROOT/'papers/recheck/results.tex').write_text(tex)
    lines=['\\begin{tabular}{lrrrr}','\\toprule','Policy & Complete & Cost & Queries & Plan ms \\\\','\\midrule']
    for a in ['restart','conservative','point_estimate','random','graph_entropy','class_entropy','ec2','myopic','discard_replay','lookahead2','exact']:
        x=pm.loc[a];lines.append(f"{NAMES[a]} & {100*x.complete:.1f} & {x.normalized_cost:.3f} & {x.probes:.2f} & {x.planning_ms:.2f} \\\\")
    lines+=['\\bottomrule','\\end{tabular}']
    (ROOT/'papers/repairlens/table_main.tex').write_text('\n'.join(lines))
    tex=macro('RLExactSaving',f'{100*(1-pm.loc["exact","normalized_cost"]):.1f}')
    tex+=macro('RLTwoSaving',f'{100*(1-pm.loc["lookahead2","normalized_cost"]):.1f}')
    tex+=macro('RLExactTime',f'{pm.loc["exact","planning_ms"]+pm.loc["exact","execution_ms"]:.2f}')
    tex+=macro('RLTwoTime',f'{pm.loc["lookahead2","planning_ms"]+pm.loc["lookahead2","execution_ms"]:.2f}')
    tex+=macro('RLRestartTime',f'{pm.loc["restart","execution_ms"]:.2f}')
    for meth,n in [('exact','Exact'),('lookahead2','Two')]:
        ci=claims['repairlens']['comparisons'][f'normalized_cost:{meth}-restart']
        tex+=macro('RLLow'+n,f'{-100*ci["high"]:.1f}')+macro('RLHigh'+n,f'{-100*ci["low"]:.1f}')
    (ROOT/'papers/repairlens/results.tex').write_text(tex)
    # Separate, single-axis figures. No manual colors or style presets.
    fig,ax=plt.subplots(figsize=(3.52,2.65))
    for method,mark in [('ttl','s'),('entropy','^'),('myopic','x'),('recheck','o')]:
        g=r[r.method==method].groupby('price')[['probes_per_task','success']].mean().sort_values('probes_per_task')
        ax.plot(g.probes_per_task,g.success*100,marker=mark,label=NAMES[method])
    ax.set_xlabel('Paid probes / task (including startup)');ax.set_ylabel('Exact-task success (%)')
    ax.legend(frameon=False,loc='lower right');ax.grid(alpha=.2)
    savefig(fig,'recheck_frontier')
    fig,ax=plt.subplots(figsize=(3.52,2.55))
    for method,mark in [('myopic','x'),('ttl','s'),('no_task','^'),('recheck','o')]:
        g=r[r.method==method].groupby('hazard')['objective'].mean()
        ax.plot(g.index,g.values,marker=mark,label=NAMES[method])
    ax.set_xlabel('Base drift probability');ax.set_ylabel('Weighted loss + probe cost, $J$');ax.set_ylim(0,.20);ax.legend(frameon=False,loc='lower right');ax.grid(alpha=.2)
    savefig(fig,'recheck_drift')
    fig,ax=plt.subplots(figsize=(4.2,2.6))
    bg=b.groupby(['condition','method']).objective.mean().unstack();labels=['no_drift','underestimated_drift','overestimated_drift'];xx=np.arange(3)
    for i,method in enumerate(['myopic','recheck','fresh']):ax.bar(xx+(i-1)*.24,bg.loc[labels,method],.24,label=NAMES[method])
    ax.set_xticks(xx,['No drift','Underestimate','Overestimate']);ax.set_ylabel('$J$');ax.legend(frameon=False);savefig(fig,'recheck_misspecification')
    fig,ax=plt.subplots(figsize=(3.52,2.75))
    family=['sparse','overlap','general','nuisance','coupled','expensive'];xx=np.arange(len(family))
    for method,mark in [('class_entropy','s'),('myopic','^'),('lookahead2','o'),('exact','x')]:
        g=p[p.method==method].groupby('family').normalized_cost.mean().reindex(family)
        ax.plot(xx,g,marker=mark,label=NAMES[method])
    ax.axhline(1,linestyle='--',linewidth=.8);ax.set_xticks(xx,['Sparse','Overlap','General','Nuisance','Coupled','Costly'],rotation=25,ha='right')
    ax.set_ylabel('Assigned cost / restart');ax.legend(frameon=False,ncol=1);ax.grid(alpha=.2)
    savefig(fig,'repairlens_families')
    fig,ax=plt.subplots(figsize=(3.52,2.65))
    tau=np.geomspace(.0005,20,150)
    for method,mark in [('myopic','^'),('class_entropy','s'),('lookahead2','o'),('exact','x')]:
        ratio=(pm.loc[method,'planning_ms']+tau*pm.loc[method,'cost'])/(tau*pm.loc['restart','cost'])
        ax.plot(tau,ratio,label=NAMES[method])
    ax.axhline(1,linestyle='--',linewidth=.8);ax.set_xscale('log');ax.set_yscale('log');ax.set_ylim(.5,300)
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value,pos:f'{value:g}'))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value,pos:f'{value:g}'))
    ax.set_xlabel('Hypothetical ms / assigned cost unit');ax.set_ylabel('Modeled time / restart time');ax.legend(frameon=False);ax.grid(alpha=.2)
    savefig(fig,'repairlens_latency_model')
    fig,ax=plt.subplots(figsize=(3.52,2.5))
    vals=q.groupby('condition').complete.mean().reindex(['covered','truth_omitted'])*100
    ax.bar(['True model included','True mask omitted'],vals)
    for i,v in enumerate(vals):ax.text(i,v+2,f'{v:.1f}%',ha='center')
    ax.set_ylim(0,114);ax.set_ylabel('Complete restoration (%)');savefig(fig,'repairlens_support')
    report=['# Executed-result summary','', '**All intervals are descriptive and conditional on the fixed generator.**','',
            '## ReCheck','',rm[['success','task_loss','probes_per_task','objective','cpu_ms']].to_markdown(),'',
            '## RepairLens','',pm[['complete','normalized_cost','probes','planning_ms','execution_ms']].to_markdown(),'',
            '## Limitations exposed by execution','',
            '- ReCheck improves weighted objective but not every unweighted success comparison.',
            '- RepairLens reduces assigned operation cost, but exact and two-step planning are slower in measured local CPU time than restart.',
            '- RepairLens support omission produces incomplete restoration; the conditional guarantee does not survive missing hypotheses.',
            '- Known finite models, ideal exact observations and deterministic synthetic workers are not end-to-end LLM or public benchmark evidence.']
    (ROOT/'docs/EXECUTED_RESULTS.md').write_text('\n'.join(report))
    print(json.dumps({k:claims[k].get('comparisons',{}) for k in ['recheck','repairlens']},indent=2))

if __name__=='__main__':main()
