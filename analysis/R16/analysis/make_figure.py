"""Rebuild the descriptive figure from local table outputs; no model/network call."""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt

def main():
    root=Path(__file__).resolve().parents[1]
    with (root/'analysis/paper_results/by_model.csv').open(encoding='utf-8') as f: rows=list(csv.DictReader(f))
    labels=['GPT-4.1','GPT-4o','4o-mini','GPT-5','M-Large','M-Nemo']
    full=np.array([int(r['source_full']) for r in rows]); conflict=np.array([int(r['conflicts']) for r in rows])
    plt.rcParams['pdf.fonttype']=42;plt.rcParams['ps.fonttype']=42
    fig,ax=plt.subplots(figsize=(3.38,2.25));x=np.arange(len(rows))
    ax.bar(x-.19,full,width=.38,label='Full progress')
    ax.bar(x+.19,conflict,width=.38,hatch='///',label='Effect conflict')
    ax.set_xticks(x,labels,rotation=28,ha='right',fontsize=9);ax.tick_params(axis='y',labelsize=9)
    ax.set_ylabel('Records (48 per model label)',fontsize=9);ax.set_ylim(0,58);ax.set_yticks([0,12,24,36,48])
    ax.legend(loc='upper center',ncol=2,fontsize=9,frameon=False,handlelength=1.1,columnspacing=.8)
    for i,n in enumerate(conflict):ax.text(i+.19,n+1,str(n),ha='center',fontsize=9)
    fig.tight_layout(pad=.4)
    for suffix in ['pdf','svg','png']:fig.savefig(root/f'paper/figures/model_counts.{suffix}',dpi=200)
    plt.close(fig)
if __name__=='__main__':main()
