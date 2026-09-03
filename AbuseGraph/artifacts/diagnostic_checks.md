# AbuseGraph diagnostic checks
These are diagnostic checks on the fixed generated corpus. They are not additional holdout tuning.

## 1. Network-only vs full detector
- Network-only ROC-AUC: 0.8878
- Network-only Average Precision: 0.2078
- Full AbuseGraph ROC-AUC: 0.9983
- Full AbuseGraph Average Precision: 0.9594
Interpretation: relationship evidence is informative, but the strongest signal comes from combining relationship and behavioral/loss evidence.

## 2. Legitimate shared-resource check
- Legitimate shared-resource customers: 2229
- Mean score: 0.458
- 95th percentile score: 0.534
- Flagged at current 0.63 diagnostic threshold: 29 (1.30%)
Interpretation: shared infrastructure alone does not produce a uniformly high score, but some legitimate clusters remain hard cases and must be reviewed rather than auto-blocked.

## 3. Mixed-case check
- Mixed customers: 100
- Mean score: 0.583
- Flagged at 0.63: 30 (30.00%)
Interpretation: mixed cases sit between normal sharing and clear abuse; the system should surface them for investigation rather than treat every connected member as guilty.

## 4. Ring archetypes
| intended_pattern      |   temporal |   behavior |   score |
|:----------------------|-----------:|-----------:|--------:|
| amount_pattern        |      0.004 |      0.849 |   0.803 |
| behavioral_similarity |      0     |      0.86  |   0.765 |
| burst                 |      0.069 |      0.648 |   0.781 |
| slow_burn             |      0.006 |      0.628 |   0.724 |

Interpretation: temporal coordination is intentionally weak for slow-burn, amount-pattern, and behavioral-similarity rings. This prevents the detector from depending on a single 60-minute burst signal.