ALLOWED_RISK = {"LOW", "MEDIUM", "HIGH"}
ALLOWED_ACTION = {"NO_ACTION", "MANUAL_REVIEW", "PRIORITY_REVIEW"}
VALID_PATH_PREFIXES = {
    "evidence.cluster_risk_score", "evidence.account_count",
    "evidence.shared_devices", "evidence.shared_payment_instruments",
    "evidence.shared_addresses", "evidence.refund_rate",
    "evidence.chargeback_rate", "evidence.temporal_coordination",
    "evidence.behavior_similarity", "evidence.potential_exposure",
    "members[*].risk_band"
}

def verify(case, output):
    errors = []
    if not isinstance(output, dict):
        return False, ["output must be an object"]

    if output.get("risk_assessment") not in ALLOWED_RISK:
        errors.append("invalid risk_assessment")
    if output.get("recommended_action") not in ALLOWED_ACTION:
        errors.append("invalid recommended_action")

    for section in ("key_findings", "counter_evidence"):
        if not isinstance(output.get(section, []), list):
            errors.append(f"{section} must be a list")
            continue
        for i, item in enumerate(output[section]):
            if not item.get("evidence_paths"):
                errors.append(f"{section}[{i}] has no evidence path")
            for path in item.get("evidence_paths", []):
                if path not in VALID_PATH_PREFIXES:
                    errors.append(f"unsupported evidence path: {path}")

    valid_ids = {m["customer_id"] for m in case["members"]}
    for cid in output.get("priority_members", []):
        if cid not in valid_ids:
            errors.append(f"hallucinated customer id: {cid}")

    return not errors, errors
