import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai.pipeline import InvestigationPipeline
from ai.fallback import deterministic_investigator
from detection.abusegraph import run_abusegraph
from detection.baseline import run_baseline
from evaluation.metrics import customer_metrics


def load_data():
    d = ROOT / "output"
    read = lambda n: pd.read_csv(d / n)
    return (read("customers.csv"), read("transactions.csv"), read("refunds.csv"), read("chargebacks.csv"),
            read("customer_device_links.csv"), read("customer_address_links.csv"), read("customer_payment_links.csv"))


def test_ai_verifier():
    case = json.loads((ROOT / "data/demo_case.json").read_text())
    good = InvestigationPipeline(deterministic_investigator).run(case)
    assert good["status"] == "VERIFIED_AI"

    def hallucinating(c):
        out = deterministic_investigator(c)
        out["priority_members"] = ["C999999"]
        return out

    bad = InvestigationPipeline(hallucinating).run(case)
    assert bad["status"] == "FALLBACK"
    assert bad["verification_errors"]


def test_graph_beats_behavior_baseline():
    customers, txn, refunds, chargebacks, dl, al, pl = load_data()
    txn["timestamp"] = pd.to_datetime(txn.timestamp)
    cutoff = txn.timestamp.quantile(0.70)
    train = txn[txn.timestamp <= cutoff]
    ref = refunds[refunds.txn_id.isin(train.txn_id)]
    cb = chargebacks[chargebacks.txn_id.isin(train.txn_id)]

    baseline = run_baseline(customers, train, ref, cb)
    _, _, _, members = run_abusegraph(customers, train, ref, cb, dl, al, pl)
    graph = customers[["customer_id", "label"]].copy()
    scores = members.groupby("customer_id").risk_score.max()
    graph["risk_score"] = graph.customer_id.map(scores).fillna(0)

    bm = customer_metrics(baseline)
    gm = customer_metrics(graph, threshold=0.55)
    assert gm["f1"] > bm["f1"]
    assert gm["precision"] > bm["precision"]


def test_mixed_customers_contain_both_transaction_behaviors():
    customers, txn, *_ = load_data()
    mixed_ids = set(customers.loc[customers.label == "MIXED", "customer_id"])
    mixed = txn[txn.customer_id.isin(mixed_ids)]
    assert not mixed.empty
    assert set(mixed.ground_truth_behavior.unique()) == {"NORMAL", "ABUSIVE"}
