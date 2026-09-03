from __future__ import annotations
import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score


def customer_metrics(df, label_col="label", score_col="risk_score", positive="ABUSE_RING", threshold=0.5):
    y = (df[label_col] == positive).astype(int)
    score = df[score_col].astype(float).to_numpy()
    pred = (score >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    result = {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "flagged": int(pred.sum()),
        "positives": int(y.sum()),
    }
    if y.sum() and y.sum() < len(y):
        result["roc_auc"] = float(roc_auc_score(y, score))
        result["average_precision"] = float(average_precision_score(y, score))
    else:
        result["roc_auc"] = None
        result["average_precision"] = None
    return result


def false_positive_cost(df, amount_by_customer, threshold=0.5, fp_cost=75.0):
    flagged = df[df.risk_score >= threshold]
    false_positive = flagged[flagged.label.isin(["NORMAL", "LEGITIMATE_SHARED_RESOURCE", "MIXED"])]
    missed = df[(df.label == "ABUSE_RING") & (df.risk_score < threshold)]
    missed_exposure = float(amount_by_customer.reindex(missed.customer_id).fillna(0).sum())
    return {
        "false_positive_count": int(len(false_positive)),
        "false_positive_operational_cost": float(len(false_positive) * fp_cost),
        "missed_abuse_exposure": missed_exposure,
        "total_flagged": int(len(flagged)),
    }
