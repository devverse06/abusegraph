def deterministic_investigator(case):
    e = case["evidence"]
    high = [m["customer_id"] for m in case["members"] if m["risk_band"] == "HIGH"]
    review = sum(m["risk_band"] == "REVIEW" for m in case["members"])

    risk = "HIGH" if e["cluster_risk_score"] >= .75 else "MEDIUM" if e["cluster_risk_score"] >= .55 else "LOW"
    action = {"HIGH":"PRIORITY_REVIEW","MEDIUM":"MANUAL_REVIEW","LOW":"NO_ACTION"}[risk]

    findings = [{
        "claim": f"The candidate cluster contains {e['account_count']} accounts.",
        "evidence_paths": ["evidence.account_count"]
    }]
    if e["shared_devices"]:
        findings.append({
            "claim": f"{e['shared_devices']} shared device resource(s) connect members.",
            "evidence_paths": ["evidence.shared_devices"]
        })
    if e["shared_payment_instruments"]:
        findings.append({
            "claim": f"{e['shared_payment_instruments']} shared payment instrument resource(s) connect members.",
            "evidence_paths": ["evidence.shared_payment_instruments"]
        })
    findings.append({
        "claim": f"Potential exposure associated with refunds or chargebacks is ₹{e['potential_exposure']:.2f}.",
        "evidence_paths": ["evidence.potential_exposure"]
    })

    counter = []
    if e["temporal_coordination"] < .5:
        counter.append({
            "claim": "Strong temporal coordination is not established by the current evidence.",
            "evidence_paths": ["evidence.temporal_coordination"]
        })
    if review:
        counter.append({
            "claim": f"{review} member(s) remain in REVIEW rather than HIGH.",
            "evidence_paths": ["members[*].risk_band"]
        })

    return {
        "summary": f"{risk}-risk investigation candidate involving {e['account_count']} accounts.",
        "risk_assessment": risk,
        "key_findings": findings,
        "counter_evidence": counter,
        "uncertainty": [
            "Shared resources can have legitimate explanations.",
            "Additional investigation is required before enforcement."
        ],
        "recommended_action": action,
        "priority_members": high[:5],
    }
