#!/usr/bin/env python3
"""Minimal MCP-style stdio server for listing_compliance_check (v0.1).

Speaks a tiny JSON-RPC subset over stdin/stdout:
  {"jsonrpc":"2.0","id":1,"method":"tools/list"}
  {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"listing_compliance_check","arguments":{...}}}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import check  # noqa: E402

SCHEMA = json.loads((Path(__file__).parent / "tool_schema.json").read_text(encoding="utf-8"))


def handle(msg: dict) -> dict:
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
                        "annotations": SCHEMA.get("annotations", {"readOnlyHint": True}),
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
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
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
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        out = handle(msg)
        if out:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
