from .fallback import deterministic_investigator
from .verifier import verify

class InvestigationPipeline:
    def __init__(self, ai_function=None):
        self.ai_function = ai_function

    def run(self, case):
        if self.ai_function is None:
            return {
                "status": "FALLBACK",
                "reason": "No LLM credentials/provider configured",
                "output": deterministic_investigator(case),
            }

        try:
            output = self.ai_function(case)
        except Exception as exc:
            return {
                "status": "FALLBACK",
                "reason": f"LLM call failed: {type(exc).__name__}: {exc}",
                "output": deterministic_investigator(case),
            }

        ok, errors = verify(case, output)
        if not ok:
            return {
                "status": "FALLBACK",
                "reason": "LLM output failed evidence verification",
                "verification_errors": errors,
                "output": deterministic_investigator(case),
            }

        return {
            "status": "VERIFIED_AI",
            "reason": "LLM output passed evidence verification",
            "output": output,
        }
