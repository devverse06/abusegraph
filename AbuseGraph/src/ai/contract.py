SYSTEM_PROMPT = """
You are an abuse-risk investigation assistant inside a financial-risk workflow.
Use ONLY facts present in the supplied case JSON.
Never invent customers, resources, amounts, counts, dates, or relationships.
Do not state that abuse is proven; distinguish evidence from suspicion.
Mention meaningful counter-evidence and uncertainty.
Every concrete finding must cite one or more allowed evidence_paths.
Never recommend automatic blocking or punishment; recommend investigation only.
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string"
        },
        "risk_assessment": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"]
        },
        "key_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string"
                    },
                    "evidence_paths": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "claim",
                    "evidence_paths"
                ]
            }
        },
        "counter_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string"
                    },
                    "evidence_paths": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "claim",
                    "evidence_paths"
                ]
            }
        },
        "uncertainty": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "recommended_action": {
            "type": "string",
            "enum": [
                "NO_ACTION",
                "MANUAL_REVIEW",
                "PRIORITY_REVIEW"
            ]
        },
        "priority_members": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "summary",
        "risk_assessment",
        "key_findings",
        "counter_evidence",
        "uncertainty",
        "recommended_action",
        "priority_members"
    ]
}