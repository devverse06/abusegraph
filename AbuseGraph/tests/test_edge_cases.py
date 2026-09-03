import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai.fallback import deterministic_investigator
from ai.pipeline import InvestigationPipeline
from ai.verifier import verify
from detection.abusegraph import _temporal_coordination, build_graph, run_abusegraph


def customers(ids):
    return pd.DataFrame({
        "customer_id": ids,
        "label": ["NORMAL"] * len(ids),
    })


def empty_links(col):
    return pd.DataFrame(columns=["customer_id", col])


def base_case():
    return {
        "case_id": "G-TEST",
        "evidence": {
            "cluster_risk_score": 0.8,
            "account_count": 3,
            "shared_devices": 2,
            "shared_payment_instruments": 1,
            "shared_addresses": 1,
            "refund_rate": 0.4,
            "chargeback_rate": 0.2,
            "temporal_coordination": 0.2,
            "behavior_similarity": 0.8,
            "potential_exposure": 10000.0,
        },
        "members": [
            {"customer_id": "C1", "risk_score": 0.8, "risk_band": "HIGH"},
            {"customer_id": "C2", "risk_score": 0.6, "risk_band": "REVIEW"},
            {"customer_id": "C3", "risk_score": 0.4, "risk_band": "LOW"},
        ],
    }


def test_single_customer_has_no_graph_edges():
    g = build_graph(
        pd.DataFrame({"customer_id": ["C1"], "device_id": ["D1"]}),
        empty_links("address_id"),
        empty_links("instrument_id"),
        customers(["C1"]),
    )
    assert list(g.nodes) == ["C1"]
    assert g.number_of_edges() == 0


def test_legitimate_shared_device_alone_does_not_create_edge():
    g = build_graph(
        pd.DataFrame({"customer_id": ["C1", "C2"], "device_id": ["D1", "D1"]}),
        empty_links("address_id"),
        empty_links("instrument_id"),
        customers(["C1", "C2"]),
    )
    assert g.number_of_edges() == 0


def test_two_independent_shared_resources_create_edge():
    g = build_graph(
        pd.DataFrame({"customer_id": ["C1", "C2"], "device_id": ["D1", "D1"]}),
        pd.DataFrame({"customer_id": ["C1", "C2"], "address_id": ["A1", "A1"]}),
        empty_links("instrument_id"),
        customers(["C1", "C2"]),
    )
    assert g.has_edge("C1", "C2")
    assert g["C1"]["C2"]["device"] == 1
    assert g["C1"]["C2"]["address"] == 1


def test_high_degree_single_resource_does_not_connect_everyone():
    g = build_graph(
        pd.DataFrame({"customer_id": ["C1", "C2", "C3", "C4"], "device_id": ["D1"] * 4}),
        empty_links("address_id"),
        empty_links("instrument_id"),
        customers(["C1", "C2", "C3", "C4"]),
    )
    assert g.number_of_edges() == 0


def test_disconnected_resource_groups_remain_disconnected():
    g = build_graph(
        pd.DataFrame({"customer_id": ["C1", "C2", "C3", "C4"], "device_id": ["D1", "D1", "D2", "D2"]}),
        pd.DataFrame({"customer_id": ["C1", "C2", "C3", "C4"], "address_id": ["A1", "A1", "A2", "A2"]}),
        empty_links("instrument_id"),
        customers(["C1", "C2", "C3", "C4"]),
    )
    assert g.has_edge("C1", "C2")
    assert g.has_edge("C3", "C4")
    assert not g.has_edge("C1", "C3")


def test_missing_relationship_data_degrades_to_no_clusters():
    cust = customers(["C1", "C2"])
    txn = pd.DataFrame(columns=["txn_id", "customer_id", "amount", "timestamp", "merchant_category"])
    empty = pd.DataFrame(columns=["txn_id"])
    g, features, clusters, members = run_abusegraph(
        cust, txn, empty, empty, empty_links("device_id"), empty_links("address_id"), empty_links("instrument_id")
    )
    assert g.number_of_edges() == 0
    assert clusters.empty
    assert members.empty


def test_temporal_same_hour_counts_as_coordination():
    txn = pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "timestamp": ["2026-01-01 12:05:00", "2026-01-01 12:59:59"],
    })
    assert _temporal_coordination(txn, {"C1", "C2"}) == 1.0


def test_temporal_next_hour_does_not_count_as_same_hour():
    txn = pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "timestamp": ["2026-01-01 12:00:00", "2026-01-01 13:00:00"],
    })
    assert _temporal_coordination(txn, {"C1", "C2"}) == 0.0


def test_temporal_no_transactions_returns_zero():
    txn = pd.DataFrame(columns=["customer_id", "timestamp"])
    assert _temporal_coordination(txn, {"C1", "C2"}) == 0.0


def test_verifier_rejects_unsupported_evidence_path():
    case = base_case()
    output = deterministic_investigator(case)
    output["key_findings"][0]["evidence_paths"] = ["database.secret_field"]
    ok, errors = verify(case, output)
    assert not ok
    assert any("unsupported evidence path" in e for e in errors)


def test_verifier_rejects_invalid_action():
    case = base_case()
    output = deterministic_investigator(case)
    output["recommended_action"] = "BLOCK"
    ok, errors = verify(case, output)
    assert not ok
    assert "invalid recommended_action" in errors


def test_verifier_rejects_hallucinated_customer_id():
    case = base_case()
    output = deterministic_investigator(case)
    output["priority_members"] = ["C_HALLUCINATED"]
    ok, errors = verify(case, output)
    assert not ok
    assert any("hallucinated customer id" in e for e in errors)


def test_verifier_rejects_finding_without_evidence_path():
    case = base_case()
    output = deterministic_investigator(case)
    output["key_findings"].append({"claim": "unsupported claim", "evidence_paths": []})
    ok, errors = verify(case, output)
    assert not ok
    assert any("has no evidence path" in e for e in errors)


def test_pipeline_falls_back_on_malformed_ai_output():
    case = base_case()

    def malformed(_case):
        return ["not", "an", "object"]

    result = InvestigationPipeline(malformed).run(case)
    assert result["status"] == "FALLBACK"
    assert result["reason"] == "LLM output failed evidence verification"
    assert result["output"]["recommended_action"] in {"NO_ACTION", "MANUAL_REVIEW", "PRIORITY_REVIEW"}


def test_pipeline_falls_back_when_ai_provider_raises():
    case = base_case()

    def broken(_case):
        raise TimeoutError("provider timeout")

    result = InvestigationPipeline(broken).run(case)
    assert result["status"] == "FALLBACK"
    assert "LLM call failed" in result["reason"]
    assert "output" in result
