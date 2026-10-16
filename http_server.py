#!/usr/bin/env python3
"""HTTPS-ready HTTP JSON-RPC front for listing_compliance_check (v0.1).

POST /mcp   — MCP JSON-RPC (initialize | tools/list | tools/call)
GET  /health — liveness
GET  /      — short info

Bind 0.0.0.0:$PORT (default 8080). Put behind any TLS terminator (Caddy, nginx, Cloudflare, Railway, Fly).
Optional bearer: set MCP_AUTH_TOKEN; clients send Authorization: Bearer <token>.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import check  # noqa: E402

SCHEMA = json.loads((Path(__file__).parent / "tool_schema.json").read_text(encoding="utf-8"))
AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "8080"))


def handle_rpc(msg: dict) -> dict:
    mid = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "listing-compliance", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "tools": [
                    {
                        "name": SCHEMA["name"],
                        "description": SCHEMA["description"],
                        "inputSchema": SCHEMA["inputSchema"],
                        "annotations": SCHEMA.get(
                            "annotations", {"readOnlyHint": True}
                        ),
                    }
                ]
            },
        }
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name != "listing_compliance_check":
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "error": {"code": -32601, "message": f"Unknown tool: {name}"},
            }
        try:
            result = check(
                platform=args["platform"],
                title=args.get("title", ""),
                description=args.get("description", ""),
                category=args.get("category", ""),
                claims=args.get("claims", ""),
                language=args.get("language", "zh-Hant-HK"),
            )
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False),
                        }
                    ],
                    "structuredContent": result,
                    "isError": False,
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            }
    if method == "notifications/initialized":
        return {}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "listing-compliance/0.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _auth_ok(self) -> bool:
        if not AUTH_TOKEN:
            return True
        h = self.headers.get("Authorization", "")
        return h == f"Bearer {AUTH_TOKEN}"

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, b"")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, json.dumps({"ok": True}).encode())
            return
        if path in ("/", "/mcp"):
            info = {
                "name": "listing-compliance",
                "version": "0.1.0",
                "transport": "http-jsonrpc",
                "endpoint": "POST /mcp",
                "tools": [SCHEMA["name"]],
                "auth": "bearer" if AUTH_TOKEN else "none",
            }
            self._send(200, json.dumps(info, ensure_ascii=False).encode())
            return
        self._send(404, json.dumps({"error": "not found"}).encode())

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/mcp", "/"):
            self._send(404, json.dumps({"error": "not found"}).encode())
            return
        if not self._auth_ok():
            self._send(401, json.dumps({"error": "unauthorized"}).encode())
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            msg = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(
                400,
                json.dumps(
                    {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
                ).encode(),
            )
            return
        if isinstance(msg, list):
            outs = [handle_rpc(m) for m in msg if isinstance(m, dict)]
            outs = [o for o in outs if o]
            self._send(200, json.dumps(outs, ensure_ascii=False).encode())
            return
        out = handle_rpc(msg)
        if not out:
            self._send(202, b"")
            return
        self._send(200, json.dumps(out, ensure_ascii=False).encode())


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    httpd = ThreadingHTTPServer((host, PORT), Handler)
    sys.stderr.write(
        f"listing-compliance HTTP on http://{host}:{PORT}/mcp "
        f"(auth={'on' if AUTH_TOKEN else 'off'})\n"
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
