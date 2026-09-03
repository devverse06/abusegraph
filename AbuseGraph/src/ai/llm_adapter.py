"""Provider-neutral Gemini adapter using the official REST generateContent API.

The API key is read only on the server. If no key is configured, the demo uses
its deterministic evidence-grounded fallback.
"""

import json
import os
import urllib.request
import urllib.error
from .contract import SYSTEM_PROMPT, OUTPUT_SCHEMA


class LLMAdapter:
    def __init__(self, generate_json=None):
        self.generate_json = generate_json or gemini_generate_json

    def investigate(self, case):
        return self.generate_json({
            "system": SYSTEM_PROMPT,
            "schema": OUTPUT_SCHEMA,
            "case": case,
        })


def gemini_generate_json(payload):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    prompt = (
        payload["system"]
        + "\n\nCASE JSON:\n"
        + json.dumps(payload["case"], ensure_ascii=False)
        + "\n\nReturn only the requested JSON object."
    )
    body = {
        "systemInstruction": {"parts": [{"text": payload["system"]}]},
        "contents": [{"parts": [{"text": "CASE JSON:\n" + json.dumps(payload["case"], ensure_ascii=False)}]}],
        "generationConfig": {
    "responseMimeType": "application/json",
    "responseSchema": payload["schema"],
    "temperature": 0.1,
},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail[:300]}") from exc

    candidates = raw.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = next((p.get("text") for p in parts if p.get("text")), None)
    if not text:
        raise RuntimeError("Gemini returned no text output")
    return json.loads(text)


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
