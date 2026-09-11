from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .core import ModelAccessError, OrderClerkError, OrderService


STATIC_DIR = Path(__file__).resolve().parent.parent / "web"


class OrderClerkHandler(BaseHTTPRequestHandler):
    service: OrderService
    server_version = "OrderClerk/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(f"[orderclerk] {self.address_string()} {format % args}")

    def _json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int) -> None:
        self._json({"error": message}, status)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"ok": True, "provider": self.service.provider()})
            return
        if path == "/api/state":
            self._json(self.service.state())
            return
        match = re.fullmatch(r"/api/orders/(\d+)/picking-list\.csv", path)
        if match:
            try:
                csv_body = self.service.picking_list_csv(int(match.group(1))).encode("utf-8")
            except OrderClerkError as error:
                self._error(str(error), HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition", f"attachment; filename=order-{match.group(1)}-picking-list.csv"
            )
            self.send_header("Content-Length", str(len(csv_body)))
            self.end_headers()
            self.wfile.write(csv_body)
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/orders/process":
            self._error("Not found.", HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 262_144:
                raise OrderClerkError("Request body must be valid JSON under 256 KB.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self.service.submit(
                str(payload.get("external_ref", "")),
                str(payload.get("customer", "")),
                str(payload.get("message", "")),
            )
            self._json(result)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._error("Request body must be valid JSON.", HTTPStatus.BAD_REQUEST)
        except OrderClerkError as error:
            status = HTTPStatus.BAD_GATEWAY if isinstance(error, ModelAccessError) else HTTPStatus.BAD_REQUEST
            self._error(str(error), status)
        except Exception:
            self._error("The order could not be processed.", HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path == "/" else request_path.lstrip("/")
        target = (STATIC_DIR / relative).resolve()
        static_root = STATIC_DIR.resolve()
        if static_root not in target.parents and target != static_root:
            self._error("Not found.", HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self._error("Not found.", HTTPStatus.NOT_FOUND)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


def build_server(host: str, port: int, service: OrderService) -> ThreadingHTTPServer:
    handler = type("BoundOrderClerkHandler", (OrderClerkHandler,), {"service": service})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
