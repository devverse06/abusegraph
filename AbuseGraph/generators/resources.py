import random

BANKS = ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK"]
INSTRUMENT_TYPES = ["card", "upi", "wallet"]

def generate_addresses(cfg, rng):
    rows = []
    for i in range(max(40, cfg.resource_clusters + 10)):
        rows.append({
            "address_id": f"A{i+1:05d}",
            "lat": round(rng.uniform(12.85, 13.15), 6),
            "lon": round(rng.uniform(77.45, 77.75), 6),
            "address_type": rng.choices(
                ["residential", "commercial", "shared"],
                weights=[0.72, 0.18, 0.10]
            )[0],
        })
    return rows

def generate_devices(cfg, rng):
    rows = []
    count = max(80, cfg.customers // 2)
    for i in range(count):
        rows.append({
            "device_id": f"D{i+1:05d}",
            "device_fingerprint": f"fp_{rng.getrandbits(64):016x}",
            "first_seen_date": f"2025-{rng.randint(1,12):02d}-01",
        })
    return rows

def generate_payment_instruments(cfg, rng):
    rows = []
    count = max(120, cfg.customers)
    for i in range(count):
        kind = rng.choice(INSTRUMENT_TYPES)
        rows.append({
            "instrument_id": f"P{i+1:05d}",
            "type": kind,
            "masked_identifier": (
                f"****{rng.randint(1000,9999)}" if kind == "card"
                else f"upi_{rng.randint(100000,999999)}"
            ),
            "issuing_bank": rng.choice(BANKS),
        })
    return rows
