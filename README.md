# listing_compliance_check

Minimal MCP tool: check a marketplace listing draft against merchant compliance rules.

**Platforms (v0.1):** `hktvmall`, `shopee_my`  
**Engine:** keyword + context heuristics (not legal advice)

## Quick CLI

```bash
python3 engine.py --platform hktvmall --file sample_biotree.json
```

## MCP stdio server

Line-delimited JSON-RPC on stdin/stdout:

```bash
python3 server.py
```

Methods: `initialize`, `tools/list`, `tools/call` (`listing_compliance_check`).

Example call arguments: see `sample_biotree.json` / `tool_schema.json`.

## Files

| File | Role |
|------|------|
| `engine.py` | Rule engine |
| `server.py` | MCP stdio wrapper |
| `tool_schema.json` | Tool I/O schema + pricing hint |
| `rules_hktvmall.json` | HKTVmall rules |
| `rules_shopee_my.json` | Shopee MY rules |
| `sample_biotree.json` | Real-listing sample |

## Pricing hint

USD **$0.50–$2.00** per call (value-based).

## Disclaimer

Rules are drafts for tooling demos. Not a substitute for platform ToS or counsel.
