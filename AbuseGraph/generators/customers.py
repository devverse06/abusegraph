from datetime import datetime, timedelta


def generate_customers(cfg, rng, addresses):
    rows = []
    address_ids = [a["address_id"] for a in addresses]
    start = datetime(2025, 1, 1)

    for i in range(cfg.customers):
        cid = f"C{i+1:05d}"
        signup = start + timedelta(days=rng.randint(0, 600))
        rows.append({
            "customer_id": cid,
            "signup_date": signup,
            "kyc_status": rng.choices(["verified", "pending"], weights=[0.9, 0.1])[0],
            "home_address_id": rng.choice(address_ids),
            "label": "NORMAL",
            "ring_id": None,
        })
    return rows
