# Publish checklist (research only — no accounts opened)

## BusinessMCP
- Docs: https://businessmcp.com/guides/publish-to-marketplace
- Monetize: https://businessmcp.com/guides/monetize-mcp-server
- Submit: https://businessmcp.com/mcp-servers/submit

**List (free):** name, slug, category, description, connection URL/transport, tool list. Hand review ~1 business day. Featured optional $99/mo.

**Sell on Hub (paid per call):**
- Public HTTPS endpoint + domain proof
- `tools/list` median < 3s (fail > 6s)
- 1–50 tools; **every tool `readOnlyHint: true`**
- JSON object input schemas; pass prompt-injection scan
- Price per call USD $0.001–$10; you keep **70%**, platform **30%**
- Payouts: Stripe Connect; payable 14 days after call; paid on 15th if balance ≥ $25

**Gap for us:** need public HTTPS host (current `server.py` is stdio only).

## MCPRush
- Publishers: https://mcprush.com/for-publishers
- Docs: https://mcprush.com/docs

**Submit via Studio:** Git / npm / PyPI / container / hosted HTTPS.
- Listing: name, one-liner, ≥120-char description
- Paid: ≥1 monthly plan (price + call allowance)
- Prove ownership; human review ~48h
- Managed host: must be stateless (no local SQLite)
- Split: publisher **88%** / platform **12%** (per their site); weekly payouts

**Gap for us:** public GitHub repo or PyPI package preferred for managed hosting.

## Ready now
- [x] Tool name + schema + readOnlyHint
- [x] Working engine + sample
- [x] README / package.json / mcp.json
- [x] Public GitHub repo
- [x] HTTP JSON-RPC server (`http_server.py` + Dockerfile)
- [ ] Deploy HTTPS host (Railway/Fly/Caddy) + domain proof
- [ ] Stripe Connect (when selling)
- [ ] Your OK to open publisher accounts
