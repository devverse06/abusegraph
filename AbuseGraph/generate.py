from pathlib import Path
import random
import pandas as pd

from config import Config
from generators.resources import generate_addresses, generate_devices, generate_payment_instruments
from generators.customers import generate_customers
from generators.rings import build_resource_clusters, assign_ring_labels
from generators.transactions import generate_links_and_transactions
from validation.ground_truth import validate_outputs


def save_csv(rows, path):
    df = pd.DataFrame(rows)
    if not df.empty:
        for col in ["signup_date", "timestamp", "requested_at", "filed_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").astype("string")
    df.to_csv(path, index=False)


def main():
    cfg = Config()
    rng = random.Random(cfg.seed)
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    addresses = generate_addresses(cfg, rng)
    devices = generate_devices(cfg, rng)
    instruments = generate_payment_instruments(cfg, rng)
    customers = generate_customers(cfg, rng, addresses)
    clusters = build_resource_clusters(cfg, rng, customers, devices, addresses, instruments)
    rings = assign_ring_labels(cfg, rng, clusters)

    links_d, links_a, links_p, transactions, refunds, chargebacks = generate_links_and_transactions(
        cfg, rng, customers, devices, addresses, instruments, clusters, rings
    )

    save_csv(customers, out / "customers.csv")
    save_csv(devices, out / "devices.csv")
    save_csv(addresses, out / "addresses.csv")
    save_csv(instruments, out / "payment_instruments.csv")
    save_csv(links_d, out / "customer_device_links.csv")
    save_csv(links_a, out / "customer_address_links.csv")
    save_csv(links_p, out / "customer_payment_links.csv")
    save_csv(transactions, out / "transactions.csv")
    save_csv(refunds, out / "refunds.csv")
    save_csv(chargebacks, out / "chargebacks.csv")
    save_csv(rings, out / "rings.csv")

    validate_outputs(customers, transactions, rings)
    print(f"\nCSV files written to: {out.resolve()}")


if __name__ == "__main__":
    main()
