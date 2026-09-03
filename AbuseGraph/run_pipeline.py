from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from detection.abusegraph import build_customer_features, build_graph, score_components, score_members
from detection.baseline import run_baseline
from evaluation.metrics import customer_metrics, false_positive_cost
from case_engine import build_case


def load_data(data_dir: Path):
    read = lambda name: pd.read_csv(data_dir / name)
    return (
        read("customers.csv"), read("transactions.csv"), read("refunds.csv"),
        read("chargebacks.csv"), read("customer_device_links.csv"),
        read("customer_address_links.csv"), read("customer_payment_links.csv")
    )


def filter_links_to_cutoff(df, cutoff):
    out = df.copy()
    if "first_used" in out.columns:
        out["first_used"] = pd.to_datetime(out["first_used"], errors="coerce")
        out = out[out["first_used"] <= cutoff]
    return out


def scores_from_members(customers, members):
    out = customers[["customer_id", "label", "ring_id"]].copy()
    if members.empty:
        out["risk_score"] = 0.0
    else:
        out["risk_score"] = out.customer_id.map(
            members.groupby("customer_id").risk_score.max()
        ).fillna(0.0)
    return out


def select_threshold(df):
    best = None
    for threshold in np.arange(0.35, 0.86, 0.01):
        m = customer_metrics(df, threshold=float(threshold))
        key = (m["f1"], m["precision"], -m["flagged"])
        if best is None or key > best[0]:
            best = (key, float(threshold), m)
    return best[1], best[2]


def ring_recall(customers, rings, flagged):
    groups = customers[customers.ring_id.notna()].groupby("ring_id").customer_id.apply(set).to_dict()
    valid = set(rings.ring_id)
    total = found = 0
    for rid, members in groups.items():
        if rid not in valid:
            continue
        total += 1
        found += len(members & flagged) / max(len(members), 1) >= 0.5
    return found / max(total, 1)


def score_graph_period(customers, txn_period, refunds_period, chargebacks_period, graph,
                       device_links, address_links, payment_links):
    features, _ = build_customer_features(
        customers, txn_period, refunds_period, chargebacks_period,
        device_links, address_links, payment_links
    )
    clusters = score_components(graph, features, txn_period, refunds_period, chargebacks_period)
    members = score_members(clusters, features, graph)
    return scores_from_members(customers, members), clusters, members


def score_baseline_period(customers, txn_period, refunds_period, chargebacks_period):
    return run_baseline(customers, txn_period, refunds_period, chargebacks_period)


def choose_demo_cluster(clusters):
    if clusters.empty:
        return None
    ranked = clusters.copy()
    ranked["demo_score"] = (
        ranked["risk_score"]
        * np.log1p(ranked["account_count"])
        * np.log1p(ranked["potential_exposure"] + 1)
    )
    sweet = ranked[(ranked.account_count >= 4) & (ranked.account_count <= 10)]
    if not sweet.empty:
        ranked = sweet
    else:
        multi = ranked[ranked.account_count >= 3]
        if not multi.empty:
            ranked = multi
    return ranked.sort_values("demo_score", ascending=False).iloc[0]


def build_case_network(member_ids, device_links, address_links, payment_links, max_resources=14):
    member_ids = set(member_ids)
    nodes = [{"id": cid, "type": "customer", "label": cid} for cid in sorted(member_ids)]
    edges = []
    resource_groups = []
    for links, col, prefix, kind in [
        (device_links, "device_id", "D", "device"),
        (payment_links, "instrument_id", "P", "payment"),
        (address_links, "address_id", "A", "address"),
    ]:
        subset = links[links.customer_id.isin(member_ids)]
        for resource, group in subset.groupby(col):
            members = sorted(set(group.customer_id) & member_ids)
            if len(members) < 2:
                continue
            resource_groups.append((len(members), kind, str(resource), members))
    resource_groups.sort(reverse=True)
    for _, kind, resource, members in resource_groups[:max_resources]:
        rid = f"{kind[0].upper()}:{resource}"
        nodes.append({"id": rid, "type": "resource", "resource_type": kind, "label": resource})
        for cid in members:
            edges.append({"source": cid, "target": rid, "type": kind})
    return {"nodes": nodes, "edges": edges}


def main():
    data_dir = ROOT / "output"
    customers, txn, refunds, chargebacks, device_links, address_links, payment_links = load_data(data_dir)
    txn["timestamp"] = pd.to_datetime(txn["timestamp"])
    refunds["requested_at"] = pd.to_datetime(refunds["requested_at"])
    chargebacks["filed_at"] = pd.to_datetime(chargebacks["filed_at"])

    q70, q85 = txn.timestamp.quantile(0.70), txn.timestamp.quantile(0.85)
    train = txn[txn.timestamp <= q70].copy()
    validation = txn[(txn.timestamp > q70) & (txn.timestamp <= q85)].copy()
    test = txn[txn.timestamp > q85].copy()

    train_ids = set(train.txn_id)
    validation_ids = set(validation.txn_id)
    test_ids = set(test.txn_id)
    train_refunds = refunds[refunds.txn_id.isin(train_ids)]
    train_chargebacks = chargebacks[chargebacks.txn_id.isin(train_ids)]
    validation_refunds = refunds[refunds.txn_id.isin(validation_ids)]
    validation_chargebacks = chargebacks[chargebacks.txn_id.isin(validation_ids)]
    test_refunds = refunds[refunds.txn_id.isin(test_ids)]
    test_chargebacks = chargebacks[chargebacks.txn_id.isin(test_ids)]

    # Batch-investigation protocol: at each evaluation cutoff, the detector may use
    # all events/resources observed so far, but never customer labels. This mirrors
    # an analyst reviewing a completed batch rather than pretending every test
    # transaction was scored before it happened.
    train_devices = filter_links_to_cutoff(device_links, q70)
    train_addresses = filter_links_to_cutoff(address_links, q70)
    train_payments = filter_links_to_cutoff(payment_links, q70)
    graph_val = None

    train_plus_val = pd.concat([train, validation], ignore_index=True)
    train_plus_val_ids = set(train_plus_val.txn_id)
    cumulative_val_refunds = refunds[refunds.txn_id.isin(train_plus_val_ids)]
    cumulative_val_chargebacks = chargebacks[chargebacks.txn_id.isin(train_plus_val_ids)]
    val_devices = filter_links_to_cutoff(device_links, q85)
    val_addresses = filter_links_to_cutoff(address_links, q85)
    val_payments = filter_links_to_cutoff(payment_links, q85)
    val_graph = build_graph(val_devices, val_addresses, val_payments, customers)

    baseline_val = score_baseline_period(customers, train_plus_val, cumulative_val_refunds, cumulative_val_chargebacks)
    graph_val, val_clusters, val_members = score_graph_period(
        customers, train_plus_val, cumulative_val_refunds, cumulative_val_chargebacks, val_graph,
        val_devices, val_addresses, val_payments
    )
    baseline_threshold, baseline_val_metrics = select_threshold(baseline_val)
    graph_threshold, graph_val_metrics = select_threshold(graph_val)

    train_plus_test = pd.concat([train, validation, test], ignore_index=True)
    train_plus_test_ids = set(train_plus_test.txn_id)
    cumulative_test_refunds = refunds[refunds.txn_id.isin(train_plus_test_ids)]
    cumulative_test_chargebacks = chargebacks[chargebacks.txn_id.isin(train_plus_test_ids)]
    test_devices = filter_links_to_cutoff(device_links, txn.timestamp.max())
    test_addresses = filter_links_to_cutoff(address_links, txn.timestamp.max())
    test_payments = filter_links_to_cutoff(payment_links, txn.timestamp.max())
    test_graph = build_graph(test_devices, test_addresses, test_payments, customers)

    baseline_test = score_baseline_period(customers, train_plus_test, cumulative_test_refunds, cumulative_test_chargebacks)
    graph_test, test_clusters, test_members = score_graph_period(
        customers, train_plus_test, cumulative_test_refunds, cumulative_test_chargebacks, test_graph,
        test_devices, test_addresses, test_payments
    )

    test_amount = test.groupby("customer_id").amount.sum()
    baseline_test_metrics = customer_metrics(baseline_test, threshold=baseline_threshold)
    graph_test_metrics = customer_metrics(graph_test, threshold=graph_threshold)
    baseline_cost = false_positive_cost(baseline_test, test_amount, threshold=baseline_threshold)
    graph_cost = false_positive_cost(graph_test, test_amount, threshold=graph_threshold)
    flagged = set(graph_test.loc[graph_test.risk_score >= graph_threshold, "customer_id"])
    rings = pd.read_csv(data_dir / "rings.csv")

    metrics = {
        "evaluation_method": {
            "split": "chronological_70_train_15_validation_15_holdout",
            "protocol": "cumulative batch investigation at each cutoff",
            "validation": "threshold selected after cumulative train+validation batch",
            "holdout": "final metrics evaluated after cumulative train+validation+holdout batch; labels are evaluation-only",
        },
        "dataset": {
            "customers": len(customers), "transactions": len(txn),
            "train_transactions": len(train), "validation_transactions": len(validation),
            "held_out_test_transactions": len(test), "rings": len(rings)
        },
        "threshold_selection": {
            "method": "validation_F1_then_precision",
            "baseline": {"threshold": baseline_threshold, "validation": baseline_val_metrics},
            "abusegraph": {"threshold": graph_threshold, "validation": graph_val_metrics}
        },
        "baseline_test": {**baseline_test_metrics, **baseline_cost},
        "abusegraph_test": {
            **graph_test_metrics, **graph_cost,
            "ring_recall_at_50pct_member_coverage": ring_recall(customers, rings, flagged)
        },
        "graph": {"nodes": int(test_graph.number_of_nodes()), "edges": int(test_graph.number_of_edges()),
                  "validation_clusters": int(len(val_clusters)), "test_clusters": int(len(test_clusters))},
    }

    chosen = choose_demo_cluster(test_clusters)
    if chosen is not None:
        top_members = test_members[test_members.cluster_id == chosen.cluster_id].sort_values(
            "risk_score", ascending=False
        ).to_dict("records")
        case = build_case({
            "cluster_id": chosen.cluster_id,
            "risk_score_v2": chosen.risk_score,
            "account_count": chosen.account_count,
            "shared_devices": chosen.shared_devices,
            "shared_payment_instruments": chosen.shared_payment_instruments,
            "shared_addresses": chosen.shared_addresses,
            "refund_rate": chosen.refund_rate,
            "chargeback_rate": chosen.chargeback_rate,
            "temporal_coordination": chosen.temporal_coordination,
            "behavior_similarity": chosen.behavior_similarity,
            "potential_exposure": chosen.potential_exposure,
        }, top_members)
        case["network"] = build_case_network(
            [m["customer_id"] for m in top_members],
            test_devices, test_addresses, test_payments
        )
        case["evaluation_context"] = {
            "period": "held_out_test",
            "protocol": "cumulative batch investigation",
            "resources_available_through": str(txn.timestamp.max()),
            "customer_labels_used_by_detector": False,
        }
        (ROOT / "generated_case.json").write_text(json.dumps(case, indent=2, default=str))

    (ROOT / "artifacts" / "evaluation.json").write_text(json.dumps(metrics, indent=2))
    (ROOT / "artifacts" / "evaluation.md").write_text(
        "# AbuseGraph Evaluation\n\n"
        "This benchmark uses a chronological cumulative-batch protocol. Threshold selection happens after the validation cutoff; final metrics are evaluated after the holdout batch is available. Customer labels are evaluation-only.\n\n"
        "```json\n" + json.dumps(metrics, indent=2) + "\n```\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
