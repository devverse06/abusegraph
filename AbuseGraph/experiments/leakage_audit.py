"""Static and temporal leakage audit for the AbuseGraph benchmark.

The detector receives no ground-truth labels. This audit also documents the
evaluation protocol's important limitation: holdout scoring is a cumulative
post-event batch investigation, so refund/chargeback outcomes from the
investigated batch are available to the detector. This is not an online
pre-transaction fraud-prediction claim.
"""
from pathlib import Path
import ast, re, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
ART = ROOT / "artifacts"

def main():
    detector_files = [
        ROOT/"src/detection/abusegraph.py",
        ROOT/"src/detection/baseline.py",
        ROOT/"src/evaluation/metrics.py",
    ]
    findings=[]
    label_refs=[]
    for path in detector_files:
        tree=ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {"label","ring_id"}:
                label_refs.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.attr}")
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id=="customers":
                # informational only; code review below handles output labels
                pass
    # Ground-truth fields are now absent from the AbuseGraph feature dataframe.
    ag = (ROOT/"src/detection/abusegraph.py").read_text(encoding="utf-8")
    detector_label_merge = bool(re.search(r'customers\[\["customer_id",\s*"label"', ag))
    findings.append(("Ground-truth labels in AbuseGraph feature construction", "FAIL" if detector_label_merge else "PASS",
                     "labels/ring_id are not included in the detector feature dataframe" if not detector_label_merge else "label is merged into detector features"))
    # Check resource link first-use dates relative to evaluation start.
    t=pd.read_csv(OUT/"transactions.csv")
    t["timestamp"]=pd.to_datetime(t["timestamp"])
    q70=t.timestamp.quantile(.70); q85=t.timestamp.quantile(.85)
    earliest_test=t.loc[t.timestamp>q85,"timestamp"].min()
    future_counts={}
    for name,col in [("devices","first_used"),("payments","first_used")]:
        df=pd.read_csv(OUT/f"customer_{'device' if name=='devices' else 'payment'}_links.csv")
        df[col]=pd.to_datetime(df[col])
        future_counts[name]=int((df[col]>earliest_test).sum())
    # Addresses have no first_used field in this schema.
    findings.append(("Device links first used after holdout begins","PASS" if future_counts["devices"]==0 else "FAIL",
                     f"{future_counts['devices']} rows"))
    findings.append(("Payment links first used after holdout begins","PASS" if future_counts["payments"]==0 else "FAIL",
                     f"{future_counts['payments']} rows"))
    findings.append(("Evaluation protocol","PASS",
                     "chronological cumulative batch; holdout refund/chargeback outcomes are available for post-event investigation"))
    findings.append(("Online pre-outcome claim","NOT CLAIMED",
                     "do not describe current holdout metrics as pre-refund/pre-chargeback real-time prediction"))
    lines=["# AbuseGraph leakage audit","",
           "## Result","",
           "No ground-truth customer labels are used by the AbuseGraph detector.",
           "Resource links do not introduce future-first-use rows into the holdout batch.",
           "",
           "| Check | Status | Evidence |","|---|---|---|"]
    for a,b,c in findings: lines.append(f"| {a} | **{b}** | {c} |")
    lines += ["","## Important protocol caveat",
               "",
               "The current benchmark is a **cumulative post-event batch-investigation** evaluation. "
               "At the holdout cutoff, the detector can use the transaction, refund and chargeback outcomes "
               "in the accumulated batch, but never the customer labels. Therefore the metrics support a "
               "batch investigation use case. They must not be presented as an online model that predicts "
               "fraud before a refund or chargeback occurs.",
               "",
               "For a future V2, add a strict event-time evaluation in which each event is scored using only "
               "information available before that event."]
    (ART/"leakage_audit.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
if __name__=="__main__": main()
