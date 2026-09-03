import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "demo"))

from server import Handler, create_server


def request(server, path, method="GET"):
    request = Request(f"http://127.0.0.1:{server.server_port}{path}", method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def running_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_server_uses_port_environment_variable_and_public_bind_host(monkeypatch):
    monkeypatch.setenv("PORT", "9123")
    server = create_server()
    try:
        assert server.server_address == ("0.0.0.0", 9123)
    finally:
        server.server_close()


def test_server_defaults_to_local_development_port(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    server = create_server()
    try:
        assert server.server_address == ("0.0.0.0", 8000)
    finally:
        server.server_close()


def test_required_demo_assets_are_served():
    server, thread = running_server()
    try:
        for path in ("/demo/", "/demo/index.html", "/generated_case.json", "/artifacts/evaluation.json"):
            status, body = request(server, path)
            assert status == 200
            assert body
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_sensitive_and_arbitrary_paths_are_rejected():
    server, thread = running_server()
    try:
        blocked_paths = (
            "/.env",
            "/.git/config",
            "/src/ai/contract.py",
            "/config.py",
            "/requirements.txt",
            "/demo/server.py",
            "/output/customers.csv",
            "/generated_case.json/..",
            "/%2e%2e/.env",
        )
        for path in blocked_paths:
            status, _ = request(server, path)
            assert status == 404, path
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_sensitive_paths_are_rejected_for_head_requests():
    server, thread = running_server()
    try:
        status, _ = request(server, "/.env", method="HEAD")
        assert status == 404
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_health_endpoint_reports_application_components():
    server, thread = running_server()
    try:
        status, body = request(server, "/api/health")
        payload = __import__("json").loads(body)
        assert status == 200
        assert payload["status"] == "ok"
        assert payload["checks"] == {
            "application": "ok",
            "detector": "available",
            "verifier": "available",
            "synthetic_dataset": "available",
        }
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_investigation_rejects_invalid_requests_without_details():
    server, thread = running_server()
    try:
        invalid_requests = (
            "/api/investigate?mode=unexpected",
            "/api/investigate?mode=hallucinate&mode=unexpected",
            "/api/investigate?other=value",
        )
        for path in invalid_requests:
            status, body = request(server, path, method="POST")
            assert status == 400
            assert body == b'{"error": "invalid request"}'

        body_request = Request(
            f"http://127.0.0.1:{server.server_port}/api/investigate",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urlopen(body_request, timeout=5)
        except HTTPError as exc:
            assert exc.code == 400
            body = exc.read()
        assert body == b'{"error": "request body is not supported"}'
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()