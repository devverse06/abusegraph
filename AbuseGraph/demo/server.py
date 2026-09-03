import json
import logging
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai.fallback import deterministic_investigator
from ai.pipeline import InvestigationPipeline
from ai.llm_adapter import LLMAdapter

LOGGER = logging.getLogger("abusegraph.demo")

ALLOWED_STATIC_PATHS = {
    "/demo/",
    "/demo/index.html",
    "/generated_case.json",
    "/artifacts/evaluation.json",
}
REQUIRED_DATASET_FILES = (
    "output/customers.csv",
    "output/transactions.csv",
    "output/refunds.csv",
    "output/chargebacks.csv",
    "output/customer_device_links.csv",
    "output/customer_address_links.csv",
    "output/customer_payment_links.csv",
)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _health(self):
        dataset_available = all((ROOT / path).is_file() for path in REQUIRED_DATASET_FILES)
        checks = {
            "application": "ok",
            "detector": "available",
            "verifier": "available",
            "synthetic_dataset": "available" if dataset_available else "unavailable",
        }
        status = "ok" if dataset_available else "degraded"
        return {"status": status, "checks": checks}

    def _serve_allowed_static(self):
        path = urlparse(self.path).path
        if path == "/demo":
            self.send_response(301)
            self.send_header("Location", "/demo/")
            self.end_headers()
            return True
        if path not in ALLOWED_STATIC_PATHS:
            self._json(404, {"error": "not found"})
            return True
        super().do_GET()
        return True

    def do_GET(self):
        if urlparse(self.path).path == "/api/health":
            self._json(200, self._health())
            return
        self._serve_allowed_static()

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path not in ALLOWED_STATIC_PATHS:
            self.send_error(404, "Not Found")
            return
        super().do_HEAD()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/investigate":
            self._json(404, {"error": "not found"})
            return
        query = parse_qs(parsed.query)
        modes = query.get("mode", [])
        if any(key != "mode" for key in query) or len(modes) > 1 or (modes and modes[0] != "hallucinate"):
            self._json(400, {"error": "invalid request"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid request"})
            return
        if content_length:
            self.rfile.read(content_length)
            self._json(400, {"error": "request body is not supported"})
            return
        try:
            case = json.loads((ROOT / "generated_case.json").read_text())
            if query.get("mode") == ["hallucinate"]:
                def malicious_ai(c):
                    out = deterministic_investigator(c)
                    out["priority_members"] = ["C_HALLUCINATED"]
                    return out
                result = InvestigationPipeline(malicious_ai).run(case)
            else:
              result = InvestigationPipeline(LLMAdapter().investigate).run(case)

            LOGGER.info("AI investigation completed with status=%s", result.get("status"))

            self._json(200, result)
        except Exception as exc:
            LOGGER.exception("AI investigation failed: %s", exc)
            self._json(500, {"error": "internal server error"})


if __name__ == "__main__":
    print("AbuseGraph demo: http://127.0.0.1:8000/demo/")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
