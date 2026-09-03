# AbuseGraph Test Plan

The project has **18 automated tests**: 3 existing system tests plus 15 focused edge-case/trust-boundary tests.

## Coverage

### Core/system behavior
- AI evidence verification success and hallucinated customer rejection
- AbuseGraph improvement over the behavior baseline
- MIXED customers contain both NORMAL and ABUSIVE transactions

### Shared-resource and graph edge cases
- Single-customer graph
- Legitimate shared device alone does not create an edge
- Two independent shared resources create an edge
- High-degree single resource does not connect every customer
- Disconnected resource groups remain disconnected
- Missing relationship data produces no crash and no false cluster

### Temporal edge cases
- Activity in the same wall-clock hour counts as coordination
- Activity in the next wall-clock hour does not
- Empty transaction history returns zero temporal coordination

### AI trust-boundary failures
- Unsupported evidence paths are rejected
- Invalid actions are rejected
- Hallucinated customer IDs are rejected
- Findings without evidence paths are rejected
- Malformed AI output triggers deterministic fallback
- Provider exceptions/timeouts trigger deterministic fallback

These tests are intended to verify behavior and safety boundaries, not to optimize the detector against individual test cases.
