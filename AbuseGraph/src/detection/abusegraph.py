from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from math import log1p
from typing import Dict, Tuple

import networkx as nx
import numpy as np
import pandas as pd


def _norm(x, lo, hi):
    if hi <= lo:
        return 0.0
    return float(np.clip((x - lo) / (hi - lo), 0, 1))


def _temporal_coordination(txn: pd.DataFrame, members: set[str]) -> float:
    if txn.empty:
        return 0.0
    t = txn[txn.customer_id.isin(members)].copy()
    if t.empty:
        return 0.0
    t["hour"] = pd.to_datetime(t["timestamp"]).dt.floor("60min")
    active = t[["customer_id", "hour"]].drop_duplicates()
    counts = active.groupby("hour")["customer_id"].nunique()
    if len(counts) == 0:
        return 0.0
    return float((counts >= 2).mean())


def _behavior_similarity(txn: pd.DataFrame, refunds: pd.DataFrame, chargebacks: pd.DataFrame, members: set[str]) -> float:
    t = txn[txn.customer_id.isin(members)].copy()
    if t.empty:
        return 0.0
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    stats = t.groupby("customer_id").agg(
        median_amount=("amount", "median"),
        txn_count=("txn_id", "count"),
        category_nunique=("merchant_category", "nunique"),
    )
    ref_txns = set(refunds.txn_id) if not refunds.empty else set()
    cb_txns = set(chargebacks.txn_id) if not chargebacks.empty else set()
    t["refund_flag"] = t.txn_id.isin(ref_txns)
    t["chargeback_flag"] = t.txn_id.isin(cb_txns)
    rates = t.groupby("customer_id")[["refund_flag", "chargeback_flag"]].mean()
    stats = stats.join(rates)
    if len(stats) < 2:
        return 0.0
    cv_amount = stats.median_amount.std(ddof=0) / max(stats.median_amount.mean(), 1.0)
    cv_refund = stats.refund_flag.std(ddof=0)
    cv_cb = stats.chargeback_flag.std(ddof=0)
    similarity = 1.0 - np.clip(0.45 * cv_amount + 0.35 * cv_refund + 0.20 * cv_cb, 0, 1)
    return float(similarity)


def build_customer_features(customers, txn, refunds, chargebacks, device_links, address_links, payment_links, coordination_window=60):
    customers = customers.copy()
    txn = txn.copy()
    refunds = refunds.copy()
    chargebacks = chargebacks.copy()
    for df, col in [(txn, "timestamp"), (refunds, "requested_at"), (chargebacks, "filed_at")]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    ref_txns = set(refunds.txn_id)
    cb_txns = set(chargebacks.txn_id)
    txn["refund_flag"] = txn.txn_id.isin(ref_txns)
    txn["chargeback_flag"] = txn.txn_id.isin(cb_txns)

    agg = txn.groupby("customer_id").agg(
        txn_count=("txn_id", "count"),
        total_amount=("amount", "sum"),
        median_amount=("amount", "median"),
        refund_rate=("refund_flag", "mean"),
        chargeback_rate=("chargeback_flag", "mean"),
    )
    features = customers[["customer_id"]].merge(agg, on="customer_id", how="left")
    numeric_cols = [c for c in agg.columns if c in features.columns]
    features[numeric_cols] = features[numeric_cols].astype(float).fillna(0.0)

    for links, col in [(device_links, "device_id"), (address_links, "address_id"), (payment_links, "instrument_id")]:
        counts = links.groupby(col)["customer_id"].nunique()
        shared = counts[counts >= 2]
        per_customer = links[links[col].isin(shared.index)].groupby("customer_id")[col].nunique()
        features = features.merge(per_customer.rename(f"shared_{col}_count"), on="customer_id", how="left")
        features[f"shared_{col}_count"] = features[f"shared_{col}_count"].fillna(0)

    # Resource rarity: sharing a resource with 2 accounts is stronger than a resource used by 20.
    resource_strength = defaultdict(float)
    for links, col in [(device_links, "device_id"), (address_links, "address_id"), (payment_links, "instrument_id")]:
        counts = links.groupby(col)["customer_id"].nunique()
        for resource, freq in counts[counts >= 2].items():
            resource_strength[(col, resource)] = 1.0 / log1p(float(freq))
    return features, resource_strength


def build_graph(device_links, address_links, payment_links, customers):
    g = nx.Graph()
    customer_ids = list(customers.customer_id)
    g.add_nodes_from(customer_ids)
    edge_evidence = defaultdict(lambda: {"device": 0, "address": 0, "payment": 0})

    for links, col, kind in [
        (device_links, "device_id", "device"),
        (address_links, "address_id", "address"),
        (payment_links, "instrument_id", "payment"),
    ]:
        for resource, group in links.groupby(col):
            members = sorted(group.customer_id.unique())
            if len(members) < 2:
                continue
            for a, b in combinations(members, 2):
                edge_evidence[(a, b)][kind] += 1

    for pair, ev in edge_evidence.items():
        score = ev["device"] + ev["address"] + ev["payment"]
        if score >= 2:  # require at least two independent shared-resource signals
            g.add_edge(pair[0], pair[1], weight=score, **ev)
    return g


def score_components(graph, features, txn, refunds, chargebacks, threshold=0.55):
    txn = txn.copy()
    txn["refund_flag"] = txn.txn_id.isin(set(refunds.txn_id))
    txn["chargeback_flag"] = txn.txn_id.isin(set(chargebacks.txn_id))
    feature_by_customer = features.set_index("customer_id")
    rows = []
    for component in nx.connected_components(graph):
        if len(component) < 2:
            continue
        members = set(component)
        sub = feature_by_customer.loc[list(members)]
        avg_refund = float(sub.refund_rate.mean())
        avg_cb = float(sub.chargeback_rate.mean())
        med_amount = float(sub.median_amount.median())
        temporal = _temporal_coordination(txn, members)
        behavior = _behavior_similarity(txn, refunds, chargebacks, members)
        shared_devices = int(sub.shared_device_id_count.sum())
        shared_addresses = int(sub.shared_address_id_count.sum())
        shared_payment = int(sub.shared_instrument_id_count.sum())

        network_signal = min(1.0, (shared_devices + shared_addresses + shared_payment) / max(3.0 * len(members), 1.0))
        refund_signal = min(1.0, avg_refund / 0.35)
        cb_signal = min(1.0, avg_cb / 0.18)
        amount_signal = 1.0 if med_amount in {1999, 2499, 2999, 3499} else 0.25

        risk = float(np.clip(
            0.30 * network_signal +
            0.25 * refund_signal +
            0.15 * cb_signal +
            0.15 * temporal +
            0.10 * behavior +
            0.05 * amount_signal,
            0, 1,
        ))

        txns = txn[txn.customer_id.isin(members)]
        exposure = float(txns.loc[txns.refund_flag | txns.chargeback_flag, "amount"].sum())
        rows.append({
            "cluster_id": f"G-{min(members)}",
            "members": sorted(members),
            "account_count": len(members),
            "shared_devices": shared_devices,
            "shared_addresses": shared_addresses,
            "shared_payment_instruments": shared_payment,
            "refund_rate": avg_refund,
            "chargeback_rate": avg_cb,
            "temporal_coordination": temporal,
            "behavior_similarity": behavior,
            "potential_exposure": exposure,
            "risk_score": risk,
            "flagged": risk >= threshold,
        })
    return pd.DataFrame(rows)


def score_members(clusters, features, graph):
    if clusters.empty:
        return pd.DataFrame(columns=["customer_id", "risk_score", "risk_band"])
    feature_by_customer = features.set_index("customer_id")
    rows = []
    for _, cluster in clusters.iterrows():
        members = cluster["members"]
        for cid in members:
            f = feature_by_customer.loc[cid]
            degree = graph.degree(cid, weight="weight") if cid in graph else 0
            local_network = min(1.0, degree / 6.0)
            risk = float(np.clip(
                0.30 * cluster.risk_score +
                0.25 * min(1.0, f.refund_rate / 0.35) +
                0.20 * min(1.0, f.chargeback_rate / 0.18) +
                0.15 * local_network +
                0.10 * min(1.0, f.txn_count / 15.0),
                0, 1,
            ))
            band = "HIGH" if risk >= 0.70 else "REVIEW" if risk >= 0.50 else "LOW"
            rows.append({"customer_id": cid, "cluster_id": cluster.cluster_id, "risk_score": risk, "risk_band": band})
    return pd.DataFrame(rows)


def run_abusegraph(customers, txn, refunds, chargebacks, device_links, address_links, payment_links):
    features, _ = build_customer_features(
        customers, txn, refunds, chargebacks, device_links, address_links, payment_links
    )
    graph = build_graph(device_links, address_links, payment_links, customers)
    clusters = score_components(graph, features, txn, refunds, chargebacks)
    members = score_members(clusters, features, graph)
    return graph, features, clusters, members
