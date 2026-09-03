import pandas as pd


def validate_outputs(customers, transactions, rings):
    c = pd.DataFrame(customers)
    t = pd.DataFrame(transactions)
    r = pd.DataFrame(rings)

    print("\n=== DATASET SUMMARY ===")
    print("Customers:", len(c))
    print("Transactions:", len(t))
    print("Rings:", len(r))
    print("\nCustomer labels:")
    print(c["label"].value_counts(dropna=False))
    if not r.empty:
        print("\nRing archetypes:")
        print(r[["ring_id", "ring_type", "size", "intended_pattern"]].to_string(index=False))
    print("\nTransaction behavior:")
    print(t["ground_truth_behavior"].value_counts(dropna=False))
    print("\nAbuse transaction rate:", round((t["ground_truth_behavior"] == "ABUSIVE").mean() * 100, 2), "%")
