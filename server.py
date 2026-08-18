"""AURA web server - pure Python standard library, no third-party dependencies.

Run with: python server.py
Then open http://localhost:8000 in a browser.
Requires ANTHROPIC_API_KEY to be set as an environment variable.
"""

import json
import mimetypes
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aura_engine import (
    EXTRACTED_FIELDS,
    RISK_CRITERIA,
    assess_risk,
    check_appetite,
    draft_response,
    extract_submission,
    load_appetite_rules,
)
from demo_responses import DEMO_RESPONSES
from rationale_rules import validate_rationale
from sample_submissions import SAMPLE_SUBMISSIONS

STATIC_DIR = Path(__file__).parent / "static"
PORT = int(os.environ.get("PORT", "8000"))


def load_env_file(path=".env"):
    """Minimal .env loader (stdlib only) - does not override already-set env vars."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self._send_json(404, {"error": "not found"})
            return
        content_type, _ = mimetypes.guess_type(str(path))
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self._send_file(STATIC_DIR / "index.html")
        elif self.path == "/api/samples":
            self._send_json(200, {"samples": list(SAMPLE_SUBMISSIONS.items())})
        elif self.path == "/api/reference":
            self._send_json(
                200,
                {
                    "extraction_fields": EXTRACTED_FIELDS,
                    "appetite_rules": load_appetite_rules().get("rules", []),
                    "risk_criteria": RISK_CRITERIA,
                },
            )
        elif self.path.startswith("/static/"):
            self._send_file(STATIC_DIR / self.path[len("/static/"):])
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/analyze":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            submission_text = body.get("submission_text", "").strip()
            if not submission_text:
                self._send_json(400, {"error": "submission_text is required"})
                return

            rules = load_appetite_rules()
            live_mode = bool(os.environ.get("ANTHROPIC_API_KEY"))

            if live_mode:
                extracted = extract_submission(submission_text)
                appetite_result = check_appetite(extracted, rules)
                risk_result = assess_risk(extracted, appetite_result)
                email_draft = draft_response(extracted, appetite_result, risk_result)
            else:
                demo_key = next(
                    (k for k, v in SAMPLE_SUBMISSIONS.items() if v.strip() == submission_text),
                    None,
                )
                if demo_key is None:
                    self._send_json(
                        400,
                        {
                            "error": (
                                "No ANTHROPIC_API_KEY is configured, so this demo can only analyze "
                                "the 4 built-in sample submissions (not custom/edited text). Select "
                                "an unmodified sample from the dropdown, or set an API key for live "
                                "analysis of any text."
                            ),
                        },
                    )
                    return
                cached = DEMO_RESPONSES[demo_key]
                extracted = cached["extracted"]
                appetite_result = check_appetite(extracted, rules)
                risk_result = cached["risk"]
                email_draft = cached["email"]

            rationale_checks = validate_rationale(extracted, appetite_result, risk_result)

            self._send_json(
                200,
                {
                    "mode": "live" if live_mode else "demo",
                    "extracted": extracted,
                    "appetite": appetite_result,
                    "risk": risk_result,
                    "rationale_checks": rationale_checks,
                    "email": email_draft,
                },
            )
        except Exception as e:  # noqa: BLE001 - surface pipeline errors to the UI
            traceback.print_exc()
            self._send_json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        print(f"[server] {self.address_string()} - {fmt % args}")


def main():
    load_env_file()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "WARNING: ANTHROPIC_API_KEY is not set. Set it before analyzing a "
            "submission (see .env.example)."
        )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"AURA running at http://localhost:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
