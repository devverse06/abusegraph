from datetime import datetime, timedelta

MERCHANT_CATEGORIES = ["electronics", "fashion", "grocery", "travel", "food"]
REFUND_REASONS = ["product_issue", "customer_request", "duplicate", "other"]
CHARGEBACK_REASONS = ["fraud", "credit_not_processed", "duplicate", "product_not_received"]


def generate_links_and_transactions(cfg, rng, customers, devices, addresses, instruments, clusters, rings):
    customer_by_id = {c["customer_id"]: c for c in customers}
    ring_by_customer = {}
    ring_pattern = {}
    mixed_customers = set()
    for ring in rings:
        for cid in ring["customer_ids"]:
            ring_by_customer[cid] = ring["ring_id"]
            ring_pattern[cid] = ring["intended_pattern"]
            if ring["intended_pattern"] == "partial_abuse":
                mixed_customers.add(cid)

    device_ids = [d["device_id"] for d in devices]
    address_ids = [a["address_id"] for a in addresses]
    instrument_ids = [p["instrument_id"] for p in instruments]

    customer_device, customer_address, customer_payment = [], [], []

    for c in customers:
        cid = c["customer_id"]
        customer_device.append({
            "customer_id": cid, "device_id": rng.choice(device_ids),
            "first_used": "2025-01-01", "last_used": "2026-08-01",
            "usage_frequency": rng.randint(1, 20), "source": "baseline"
        })
        customer_address.append({
            "customer_id": cid, "address_id": c["home_address_id"],
            "relationship": "billing", "source": "baseline"
        })
        customer_payment.append({
            "customer_id": cid, "instrument_id": rng.choice(instrument_ids),
            "first_used": "2025-01-01", "last_used": "2026-08-01", "source": "baseline"
        })

    cluster_by_customer = {}
    for cluster in clusters:
        for cid in cluster["customer_ids"]:
            cluster_by_customer[cid] = cluster
            customer_device.append({
                "customer_id": cid, "device_id": cluster["device_id"],
                "first_used": "2025-06-01", "last_used": "2026-08-01",
                "usage_frequency": rng.randint(5, 50), "source": "shared_cluster"
            })
            customer_address.append({
                "customer_id": cid, "address_id": cluster["address_id"],
                "relationship": "shipping", "source": "shared_cluster"
            })
            customer_payment.append({
                "customer_id": cid, "instrument_id": cluster["instrument_id"],
                "first_used": "2025-06-01", "last_used": "2026-08-01", "source": "shared_cluster"
            })

        label = cluster["cluster_behavior"]
        for cid in cluster["customer_ids"]:
            if label == "ABUSE_RING":
                customer_by_id[cid]["label"] = "ABUSE_RING"
            elif label == "MIXED":
                customer_by_id[cid]["label"] = "MIXED"
            elif customer_by_id[cid]["label"] == "NORMAL":
                customer_by_id[cid]["label"] = "LEGITIMATE_SHARED_RESOURCE"

    for ring in rings:
        for cid in ring["customer_ids"]:
            customer_by_id[cid]["ring_id"] = ring["ring_id"]

    transactions, refunds, chargebacks = [], [], []
    start = datetime(2026, 1, 1)

    for i in range(cfg.transactions):
        cid = rng.choice(customers)["customer_id"]
        ring_id = ring_by_customer.get(cid)
        pattern = ring_pattern.get(cid)
        cluster = cluster_by_customer.get(cid)

        if cluster:
            did, pid = cluster["device_id"], cluster["instrument_id"]
            aid = cluster["address_id"]
        else:
            did, aid, pid = rng.choice(device_ids), rng.choice(address_ids), rng.choice(instrument_ids)

        amount = round(rng.choice([299, 499, 799, 999, 1499, 2499, 4999, 7999, 9999]) * rng.uniform(0.85, 1.15), 2)
        ts = start + timedelta(days=rng.randint(0, 210), minutes=rng.randint(0, 1439))

        abusive_txn = bool(ring_id)
        if cid in mixed_customers:
            abusive_txn = rng.random() < 0.45
        effective_pattern = pattern if abusive_txn else None
        if abusive_txn and effective_pattern == "burst":
            ts = start + timedelta(days=rng.randint(30, 180), minutes=rng.randint(0, 59))
        elif abusive_txn and effective_pattern == "amount_pattern":
            amount = round(rng.choice([1999, 2499, 2999, 3499]), 2)
        elif abusive_txn and effective_pattern == "behavioral_similarity":
            amount = round(rng.choice([1499, 1599, 1699, 1799]), 2)
        elif abusive_txn and effective_pattern == "partial_abuse":
            amount = round(rng.choice([999, 1499, 2499, 2999]) * rng.uniform(0.95, 1.05), 2)

        txn_id = f"T{i+1:07d}"
        transactions.append({
            "txn_id": txn_id,
            "customer_id": cid,
            "device_id": did,
            "payment_instrument_id": pid,
            "amount": amount,
            "timestamp": ts,
            "merchant_category": rng.choice(MERCHANT_CATEGORIES),
            "status": "success",
            "ground_truth_behavior": "ABUSIVE" if abusive_txn else "NORMAL",
        })

        refund_probability = 0.08
        chargeback_probability = 0.015
        if abusive_txn:
            refund_probability = 0.45 if effective_pattern != "slow_burn" else 0.38
            chargeback_probability = 0.25 if effective_pattern != "slow_burn" else 0.22
        elif customer_by_id[cid]["label"] == "MIXED":
            refund_probability = 0.10
            chargeback_probability = 0.02

        if rng.random() < refund_probability:
            refunds.append({
                "refund_id": f"RF{i+1:07d}",
                "txn_id": txn_id,
                "requested_at": ts + timedelta(hours=rng.randint(1, 72)),
                "reason_code": rng.choice(REFUND_REASONS),
                "approved": True,
            })

        if rng.random() < chargeback_probability:
            chargebacks.append({
                "chargeback_id": f"CB{i+1:07d}",
                "txn_id": txn_id,
                "filed_at": ts + timedelta(days=rng.randint(1, 10)),
                "reason_code": rng.choice(CHARGEBACK_REASONS),
                "outcome": rng.choice(["won", "lost", "pending"]),
            })

    return customer_device, customer_address, customer_payment, transactions, refunds, chargebacks
