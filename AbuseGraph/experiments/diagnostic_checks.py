import sys; sys.path.insert(0, ".")
"""Diagnostic checks for AbuseGraph's synthetic benchmark.

These checks are intentionally diagnostic, not additional model tuning.
They inspect legitimate sharing, mixed cases, archetype coverage, and
network-vs-full ablation on the generated corpus.
"""
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
from src.detection.abusegraph import build_customer_features, build_graph, score_components

BASE='output/'

def main():
    c=pd.read_csv(BASE+'customers.csv'); t=pd.read_csv(BASE+'transactions.csv')
    r=pd.read_csv(BASE+'refunds.csv'); cb=pd.read_csv(BASE+'chargebacks.csv')
    d=pd.read_csv(BASE+'customer_device_links.csv'); a=pd.read_csv(BASE+'customer_address_links.csv'); p=pd.read_csv(BASE+'customer_payment_links.csv')
    rings=pd.read_csv(BASE+'rings.csv')
    f,_=build_customer_features(c,t,r,cb,d,a,p); g=build_graph(d,a,p,c)
    cl=score_components(g,f,t,r,cb,threshold=0)
    rows=[]
    for _,x in cl.iterrows():
        for cid in x.members:
            rows.append((cid,x.cluster_id,x.risk_score,x.temporal_coordination,x.behavior_similarity,x.shared_devices,x.shared_addresses,x.shared_payment_instruments))
    cm=pd.DataFrame(rows,columns=['customer_id','cluster_id','score','temporal','behavior','sd','sa','sp'])
    cm=cm.groupby('customer_id',as_index=False).max(numeric_only=True)
    cs=c[['customer_id','label','ring_id']].merge(cm,on='customer_id',how='left').fillna(0)
    y=(cs.label=='ABUSE_RING').astype(int)
    network_raw=cs.sd+cs.sa+cs.sp; network_score=network_raw/(network_raw.max() or 1)
    report=[]
    report.append('# AbuseGraph diagnostic checks')
    report.append('These are diagnostic checks on the fixed generated corpus. They are not additional holdout tuning.')
    report.append('')
    report.append('## 1. Network-only vs full detector')
    report.append(f'- Network-only ROC-AUC: {roc_auc_score(y,network_score):.4f}')
    report.append(f'- Network-only Average Precision: {average_precision_score(y,network_score):.4f}')
    report.append(f'- Full AbuseGraph ROC-AUC: {roc_auc_score(y,cs.score):.4f}')
    report.append(f'- Full AbuseGraph Average Precision: {average_precision_score(y,cs.score):.4f}')
    report.append('Interpretation: relationship evidence is informative, but the strongest signal comes from combining relationship and behavioral/loss evidence.')
    report.append('')
    report.append('## 2. Legitimate shared-resource check')
    legit=cs[cs.label=='LEGITIMATE_SHARED_RESOURCE']
    report.append(f'- Legitimate shared-resource customers: {len(legit)}')
    report.append(f'- Mean score: {legit.score.mean():.3f}')
    report.append(f'- 95th percentile score: {legit.score.quantile(.95):.3f}')
    report.append(f'- Flagged at current 0.63 diagnostic threshold: {(legit.score>=0.63).sum()} ({(legit.score>=0.63).mean()*100:.2f}%)')
    report.append('Interpretation: shared infrastructure alone does not produce a uniformly high score, but some legitimate clusters remain hard cases and must be reviewed rather than auto-blocked.')
    report.append('')
    report.append('## 3. Mixed-case check')
    mixed=cs[cs.label=='MIXED']
    report.append(f'- Mixed customers: {len(mixed)}')
    report.append(f'- Mean score: {mixed.score.mean():.3f}')
    report.append(f'- Flagged at 0.63: {(mixed.score>=0.63).sum()} ({(mixed.score>=0.63).mean()*100:.2f}%)')
    report.append('Interpretation: mixed cases sit between normal sharing and clear abuse; the system should surface them for investigation rather than treat every connected member as guilty.')
    report.append('')
    report.append('## 4. Ring archetypes')
    rc=rings[rings.intended_pattern!='partial_abuse'][['ring_id','intended_pattern']].merge(c[['customer_id','ring_id']],on='ring_id').merge(cm,on='customer_id')
    table=rc.groupby('intended_pattern')[['temporal','behavior','score']].mean().round(3)
    report.append(table.to_markdown())
    report.append('')
    report.append('Interpretation: temporal coordination is intentionally weak for slow-burn, amount-pattern, and behavioral-similarity rings. This prevents the detector from depending on a single 60-minute burst signal.')
    open('artifacts/diagnostic_checks.md','w',encoding='utf-8').write('\n'.join(report))
    print('\n'.join(report))

if __name__=='__main__': main()
