# Final Evaluation Record

## Protocol

- 10,000 customers
- 80,000 transactions
- 139 synthetic rings
- chronological 70% / 15% / 15% split
- threshold selected on validation
- final holdout labels are never used by the detector
- cumulative batch scoring: the detector can use unlabeled observations available by the scoring cutoff

## Holdout result

| Metric | Baseline | AbuseGraph |
|---|---:|---:|
| Precision | 81.5% | **87.2%** |
| Recall | 70.4% | **90.2%** |
| F1 | 75.5% | **88.7%** |
| ROC-AUC | 0.959 | **0.994** |
| False positives | 80 | **66** |
| FP cost | ₹6,000 | **₹4,950** |
| Missed abuse exposure | ₹2.95L | **₹0.87L** |
| Ring recall @ 50% member coverage | — | **92.1%** |

## What this establishes

1. Relationship evidence improves over a behavior-only baseline on this synthetic benchmark.
2. The graph improves recall and reduces missed financial exposure.
3. False-positive cost remains visible instead of being hidden behind aggregate accuracy.
4. AI is separated from the risk score and gated by an evidence verifier.
5. A deliberately hallucinated customer ID is rejected and falls back to a deterministic investigator.

## What this does not establish

This benchmark is synthetic. It does not prove production fraud accuracy, production calibration, or real merchant ROI. Those would require real labeled outcomes, richer telemetry and calibrated business costs.
