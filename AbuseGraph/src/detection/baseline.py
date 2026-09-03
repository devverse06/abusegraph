from __future__ import annotations
import numpy as np
import pandas as pd


def run_baseline(customers, txn, refunds, chargebacks, threshold=0.50):
    txn = txn.copy()
    ref = set(refunds.txn_id)
    cb = set(chargebacks.txn_id)
    txn["refund_flag"] = txn.txn_id.isin(ref)
    txn["chargeback_flag"] = txn.txn_id.isin(cb)
    agg = txn.groupby("customer_id").agg(
        refund_rate=("refund_flag", "mean"),
        chargeback_rate=("chargeback_flag", "mean"),
        txn_count=("txn_id", "count"),
        median_amount=("amount", "median"),
    ).reset_index()
    out = customers[["customer_id", "label"]].merge(agg, on="customer_id", how="left").fillna(0)
    out["risk_score"] = np.clip(
        0.55 * np.minimum(1, out.refund_rate / 0.35) +
        0.35 * np.minimum(1, out.chargeback_rate / 0.18) +
        0.10 * np.minimum(1, out.txn_count / 15), 0, 1
    )
    out["flagged"] = out.risk_score >= threshold
    return out
