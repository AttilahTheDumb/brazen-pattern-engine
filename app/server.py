"""Zero-dependency localhost API and static UI for the Brazen Pattern Engine."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
MAX_BODY = 2 * 1024 * 1024

# Import the actual deterministic engine. The UI is a client, not a second implementation.
sys.path.insert(0, str(ROOT / "src"))
from brazen_pattern_engine.cli import _pattern  # noqa: E402
from brazen_pattern_engine.constraints import evaluate_constraints
from brazen_pattern_engine.design_ops import apply_seam_allowance, compare_patterns, grade_pattern, pattern_to_dxf, smooth_contour
from brazen_pattern_engine.errors import BrazenError  # noqa: E402
from brazen_pattern_engine.fit_corrections import is_trainable_correction, validate_fit_correction  # noqa: E402
from brazen_pattern_engine.geometry import pattern_to_svg  # noqa: E402
from brazen_pattern_engine.measurements import MeasurementSession, RepeatabilityStudy, tolerance_budget_from_study  # noqa: E402


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def response_payload(status: str, **extra: object) -> dict[str, object]:
    return {"status": status, **extra}


class Handler(BaseHTTPRequestHandler):
    server_version = "BrazenConsole/0.1"

    def log_message(self, format: str, *args: object) -> None:
        # Keep the local console quiet and avoid echoing request bodies.
        return

    def send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        data = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        allowed_origin = os.environ.get("BRAZEN_ALLOWED_ORIGIN", "")
        request_origin = self.headers.get("Origin", "")
        if allowed_origin and request_origin == allowed_origin:
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(data)

    def authorised(self) -> bool:
        secret = os.environ.get("BRAZEN_API_SECRET", "")
        if self.path == "/api/health":
            return True
        if not secret:
            bound_host = str(self.server.server_address[0])
            return bound_host in {"127.0.0.1", "::1", "localhost"}
        return self.headers.get("Authorization", "") == f"Bearer {secret}"

    def send_file(self, path: Path) -> None:
        if not path.is_file() or STATIC not in path.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = unquote(parsed.path)
        if route.startswith("/api/") and not self.authorised():
            self.send_json(response_payload("FAIL", error="API authentication required"), HTTPStatus.UNAUTHORIZED)
            return
        if route == "/api/health":
            self.send_json(response_payload("ok", engine="brazen-pattern-engine", phase="0", mode="local-only"))
            return
        if route in {"/", "/index.html"}:
            self.send_file(STATIC / "index.html")
            return
        if route.startswith("/static/"):
            relative = Path(route.removeprefix("/static/"))
            if any(part in {"", ".", ".."} for part in relative.parts):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_file(STATIC / relative)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def body_json(self) -> object:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid content length") from exc
        if length <= 0 or length > MAX_BODY:
            raise ValueError("request body must be between 1 byte and 2 MiB")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self) -> None:
        allowed_origin = os.environ.get("BRAZEN_ALLOWED_ORIGIN", "")
        request_origin = self.headers.get("Origin", "")
        self.send_response(HTTPStatus.NO_CONTENT)
        if allowed_origin and request_origin == allowed_origin:
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route.startswith("/api/") and not self.authorised():
            self.send_json(response_payload("FAIL", error="API authentication required"), HTTPStatus.UNAUTHORIZED)
            return
        try:
            payload = self.body_json()
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            if route == "/api/validate-fit":
                record = payload.get("record")
                tolerance = payload.get("toleranceFitMm")
                if not isinstance(record, dict) or not isinstance(tolerance, (int, float)):
                    raise ValueError("record and toleranceFitMm are required")
                errors = validate_fit_correction(record, tolerance_fit_mm=float(tolerance))
                self.send_json(response_payload("PASS" if not errors else "FAIL", errors=errors, trainable=is_trainable_correction(record, tolerance_fit_mm=float(tolerance))))
                return
            if route == "/api/hash-pattern":
                pattern = _pattern(payload.get("pattern", payload))
                pattern.validate_closed_contours()
                self.send_json(response_payload("PASS", patternHash=pattern.content_hash(), compilerVersion=pattern.compiler_version, svg=pattern_to_svg(pattern)))
                return
            if route == "/api/design/seam-allowance":
                pattern = apply_seam_allowance(_pattern(payload["pattern"]), allowance_mm=float(payload["allowanceMm"]))
                self.send_json(response_payload("PASS", pattern=pattern.to_dict(), svg=pattern_to_svg(pattern), patternHash=pattern.content_hash(), operation="seam-allowance"))
                return
            if route == "/api/design/grade":
                pattern = grade_pattern(_pattern(payload["pattern"]), payload.get("increments", {}))
                self.send_json(response_payload("PASS", pattern=pattern.to_dict(), svg=pattern_to_svg(pattern), patternHash=pattern.content_hash(), operation="grade"))
                return
            if route == "/api/design/smooth":
                pattern = smooth_contour(_pattern(payload["pattern"]), piece_id=str(payload["pieceId"]), contour_name=str(payload["contour"]), tension=float(payload.get("tension", 0.25)))
                self.send_json(response_payload("PASS", pattern=pattern.to_dict(), svg=pattern_to_svg(pattern), patternHash=pattern.content_hash(), operation="smooth"))
                return
            if route == "/api/design/compare":
                report = compare_patterns(_pattern(payload["reference"]), _pattern(payload["candidate"]), tolerance_mm=float(payload.get("toleranceMm", 0.1)))
                self.send_json(response_payload(str(report["status"]), report=report, operation="compare"))
                return
            if route == "/api/design/constraints":
                report = evaluate_constraints(_pattern(payload["pattern"]), payload.get("constraints", []))
                self.send_json(response_payload(str(report["status"]), report=report, operation="constraints"))
                return
            if route == "/api/export/dxf":
                pattern = _pattern(payload["pattern"])
                self.send_json(response_payload("PASS", dxf=pattern_to_dxf(pattern), patternHash=pattern.content_hash(), exportMode="inspection-only"))
                return
            if route == "/api/repeatability":
                rows = payload.get("sessions")
                if not isinstance(rows, list):
                    raise ValueError("sessions must be an array")
                sessions = tuple(MeasurementSession.from_dict(row) for row in rows)
                study = RepeatabilityStudy(sessions)
                policy = payload.get("maxRelativeTemPct")
                policy_value = float(policy) if isinstance(policy, (int, float)) else None
                results = [result.__dict__ for result in study.results(max_relative_tem_pct=policy_value)]
                budget = tolerance_budget_from_study(study, max_relative_tem_pct=policy_value)
                self.send_json(response_payload("PASS", results=results, toleranceBudget=budget.__dict__))
                return
            self.send_json(response_payload("FAIL", error="unknown API route"), HTTPStatus.NOT_FOUND)
        except (BrazenError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(response_payload("FAIL", error=str(exc)), HTTPStatus.BAD_REQUEST)


def main() -> None:
    port = int(os.environ.get("PORT", os.environ.get("BRAZEN_PORT", "8787")))
    host = os.environ.get("BRAZEN_HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    if host not in {"127.0.0.1", "::1", "localhost"} and not os.environ.get("BRAZEN_API_SECRET"):
        raise SystemExit("BRAZEN_API_SECRET is required when binding the API beyond loopback")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Brazen console listening at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
