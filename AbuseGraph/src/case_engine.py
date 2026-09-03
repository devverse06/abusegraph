from __future__ import annotations

from typing import Any

def build_case(cluster: dict[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "case_id": str(cluster["cluster_id"]),
        "case_type": "ABUSE_RING_INVESTIGATION",
        "evidence": {
            "cluster_risk_score": round(float(cluster["risk_score_v2"]), 4),
            "account_count": int(cluster["account_count"]),
            "shared_devices": int(cluster["shared_devices"]),
            "shared_payment_instruments": int(cluster["shared_payment_instruments"]),
            "shared_addresses": int(cluster["shared_addresses"]),
            "refund_rate": round(float(cluster["refund_rate"]), 4),
            "chargeback_rate": round(float(cluster["chargeback_rate"]), 4),
            "temporal_coordination": round(float(cluster["temporal_coordination"]), 4),
            "behavior_similarity": round(float(cluster["behavior_similarity"]), 4),
            "potential_exposure": round(float(cluster["potential_exposure"]), 2),
        },
        "members": [
            {
                "customer_id": str(m["customer_id"]),
                "risk_score": round(float(m["risk_score"]), 4),
                "risk_band": m["risk_band"],
            }
            for m in members
        ],
    }
