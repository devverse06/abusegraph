# AbuseGraph Architecture

## 1. Data layer

Synthetic customers, transactions, refunds and chargebacks are generated with legitimate resource sharing, abuse rings and mixed cases.

## 2. Relationship layer

A customer graph is built from shared:

- devices
- payment instruments
- addresses

The graph is intentionally explainable: an edge always has resource evidence behind it.

## 3. Detection layer

Two systems are evaluated:

**Baseline**

```text
refund rate + chargeback rate + transaction activity
```

**AbuseGraph**

```text
network evidence
+ refund behavior
+ chargeback behavior
+ temporal coordination
+ behavior similarity
+ amount-pattern signal
```

The graph is not a black-box GNN. For this buildathon, an explainable graph plus deterministic scoring gives us better evidence and easier failure analysis.

## 4. Evaluation layer

The benchmark is chronological:

```text
70% train / 15% validation / 15% holdout
```

The cumulative batch protocol allows the detector to use all **unlabeled** observations available at a scoring cutoff. Threshold selection happens on validation. The holdout labels are never used to choose the threshold.

## 5. AI layer

The LLM sees a compact evidence bundle, not the database.

It can:

- summarize evidence
- distinguish suspicion from proof
- mention counter-evidence
- prioritize members for manual review

It cannot:

- directly modify risk scores
- execute enforcement
- invent customer IDs
- cite arbitrary database paths

## 6. Verification layer

The verifier checks:

- allowed risk/action values
- evidence paths
- customer IDs
- structured output shape

Any failure produces a deterministic investigator response.

## 7. Operator layer

The demo shows:

1. benchmark metrics
2. one high-value cluster
3. customer/resource relationship graph
4. evidence breakdown
5. AI investigation
6. injected AI failure and fallback

## 8. Why not a GNN?

The buildathon rewards execution, reliability and depth. A graph representation gives us the important relational signal without introducing an opaque model that would be difficult to validate on synthetic data. A GNN can be a future extension after production labels exist.
