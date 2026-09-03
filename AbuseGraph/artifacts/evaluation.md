# AbuseGraph Evaluation

This benchmark uses a chronological cumulative-batch protocol. Threshold selection happens after the validation cutoff; final metrics are evaluated after the holdout batch is available. Customer labels are evaluation-only.

```json
{
  "evaluation_method": {
    "split": "chronological_70_train_15_validation_15_holdout",
    "protocol": "cumulative batch investigation at each cutoff",
    "validation": "threshold selected after cumulative train+validation batch",
    "holdout": "final metrics evaluated after cumulative train+validation+holdout batch; labels are evaluation-only"
  },
  "dataset": {
    "customers": 10000,
    "transactions": 80000,
    "train_transactions": 56000,
    "validation_transactions": 12000,
    "held_out_test_transactions": 12000,
    "rings": 139
  },
  "threshold_selection": {
    "method": "validation_F1_then_precision",
    "baseline": {
      "threshold": 0.7100000000000003,
      "validation": {
        "precision": 0.8108108108108109,
        "recall": 0.66,
        "f1": 0.7276736493936053,
        "flagged": 407,
        "positives": 500,
        "roc_auc": 0.939939894736842,
        "average_precision": 0.771354623114655
      }
    },
    "abusegraph": {
      "threshold": 0.6300000000000002,
      "validation": {
        "precision": 0.868,
        "recall": 0.868,
        "f1": 0.868,
        "flagged": 500,
        "positives": 500,
        "roc_auc": 0.9917662105263158,
        "average_precision": 0.926115437440858
      }
    }
  },
  "baseline_test": {
    "precision": 0.8148148148148148,
    "recall": 0.704,
    "f1": 0.7553648068669528,
    "flagged": 432,
    "positives": 500,
    "roc_auc": 0.9593272631578946,
    "average_precision": 0.8160060882575146,
    "false_positive_count": 80,
    "false_positive_operational_cost": 6000.0,
    "missed_abuse_exposure": 295225.36000000004,
    "total_flagged": 432
  },
  "abusegraph_test": {
    "precision": 0.8723404255319149,
    "recall": 0.902,
    "f1": 0.8869223205506391,
    "flagged": 517,
    "positives": 500,
    "roc_auc": 0.9941522105263157,
    "average_precision": 0.9433047774916702,
    "false_positive_count": 66,
    "false_positive_operational_cost": 4950.0,
    "missed_abuse_exposure": 87468.51999999999,
    "total_flagged": 517,
    "ring_recall_at_50pct_member_coverage": 0.920863309352518
  },
  "graph": {
    "nodes": 10000,
    "edges": 5057,
    "validation_clusters": 675,
    "test_clusters": 675
  }
}
```
