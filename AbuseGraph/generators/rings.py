from collections import defaultdict


def _pick_clusters_to_target(candidates, target_count, rng):
    picked = []
    total = 0
    for cluster in candidates:
        if total >= target_count:
            break
        picked.append(cluster)
        total += len(cluster["customer_ids"])
    return picked


def build_resource_clusters(cfg, rng, customers, devices, addresses, instruments):
    clusters = []
    shuffled = customers[:]
    rng.shuffle(shuffled)

    cursor = 0
    for i in range(cfg.resource_clusters):
        if cursor >= len(shuffled):
            break
        size = rng.randint(cfg.min_cluster_size, cfg.max_cluster_size)
        members = shuffled[cursor:cursor + size]
        cursor += size
        if len(members) < 2:
            break

        clusters.append({
            "cluster_id": f"RC{i+1:04d}",
            "customer_ids": [c["customer_id"] for c in members],
            "device_id": rng.choice(devices)["device_id"],
            "address_id": rng.choice(addresses)["address_id"],
            "instrument_id": rng.choice(instruments)["instrument_id"],
            "cluster_behavior": "LEGITIMATE_SHARED_RESOURCE",
        })
    return clusters


def assign_ring_labels(cfg, rng, clusters):
    candidates = clusters[:]
    rng.shuffle(candidates)

    target_abuse = max(1, round(cfg.customers * cfg.abuse_account_rate_target))
    target_mixed = max(1, round(cfg.customers * cfg.mixed_account_rate_target))

    abuse = _pick_clusters_to_target(candidates, target_abuse, rng)
    abuse_set = {c["cluster_id"] for c in abuse}
    remaining = [c for c in candidates if c["cluster_id"] not in abuse_set]
    mixed = _pick_clusters_to_target(remaining, target_mixed, rng)

    rings = []
    for idx, cluster in enumerate(abuse):
        ring_type = rng.choice([
            "device_ring", "address_ring", "payment_ring", "multi_resource_ring"
        ])
        archetype = rng.choice(["burst", "slow_burn", "amount_pattern", "behavioral_similarity"])
        rid = f"R{idx+1:04d}"
        rings.append({
            "ring_id": rid,
            "ring_type": ring_type,
            "size": len(cluster["customer_ids"]),
            "intended_pattern": archetype,
            "customer_ids": cluster["customer_ids"],
        })
        cluster["cluster_behavior"] = "ABUSE_RING"

    base = len(rings)
    for j, cluster in enumerate(mixed):
        rid = f"R{base+j+1:04d}"
        abused_members = cluster["customer_ids"][:max(1, len(cluster["customer_ids"]) // 2)]
        rings.append({
            "ring_id": rid,
            "ring_type": "multi_resource_ring",
            "size": len(cluster["customer_ids"]),
            "intended_pattern": "partial_abuse",
            "customer_ids": abused_members,
        })
        cluster["cluster_behavior"] = "MIXED"

    return rings
