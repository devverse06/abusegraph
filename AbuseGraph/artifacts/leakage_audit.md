# AbuseGraph leakage audit

## Result

No ground-truth customer labels are used by the AbuseGraph detector.
Resource links do not introduce future-first-use rows into the holdout batch.

| Check | Status | Evidence |
|---|---|---|
| Ground-truth labels in AbuseGraph feature construction | **PASS** | labels/ring_id are not included in the detector feature dataframe |
| Device links first used after holdout begins | **PASS** | 0 rows |
| Payment links first used after holdout begins | **PASS** | 0 rows |
| Evaluation protocol | **PASS** | chronological cumulative batch; holdout refund/chargeback outcomes are available for post-event investigation |
| Online pre-outcome claim | **NOT CLAIMED** | do not describe current holdout metrics as pre-refund/pre-chargeback real-time prediction |

## Important protocol caveat

The current benchmark is a **cumulative post-event batch-investigation** evaluation. At the holdout cutoff, the detector can use the transaction, refund and chargeback outcomes in the accumulated batch, but never the customer labels. Therefore the metrics support a batch investigation use case. They must not be presented as an online model that predicts fraud before a refund or chargeback occurs.

For a future V2, add a strict event-time evaluation in which each event is scored using only information available before that event.