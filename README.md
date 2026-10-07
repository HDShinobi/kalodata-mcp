# Kalodata MCP Server (TikTok Shop Analytics)

**English** | [Tiếng Việt](README.vi.md)

An MCP (**Model Context Protocol**) server, written in Python with the official SDK (`FastMCP`), that wraps the **Kalodata Open API**. It lets AI assistants and agents (Claude, Perplexity, Cursor, …) research TikTok Shop markets: niches, winning products, creators, viral videos, shops and livestreams.

---

## Tools

| Entity     | Ranking            | Detail               |
|------------|--------------------|----------------------|
| Category   | `category_rank`    | `category_detail`    |
| Product    | `product_rank`     | `product_detail`     |
| Creator    | `creator_rank`     | `creator_detail`     |
| Video      | `video_rank`       | `video_detail`       |
| Shop       | `shop_rank`        | `shop_detail`        |
| Livestream | `livestream_rank`  | `livestream_detail`  |

Typical flow: call a `*_rank` tool, then pass an ID from its result to the matching `*_detail` tool.

Common parameters (all optional, default from env):

- `region`: market code, e.g. `US`, `VN`, `ID`, `TH`, `MY`, `PH`, `GB`
- `language`: e.g. `en-US`, `vi-VN`
- `currency`: e.g. `USD`, `VND`
- `date_range`: e.g. `last7Day`
- Rank tools also take `sort_field` (default `{"field": "revenue", "type": "DESC"}`), `page_number` and `page_size`.

Transports: **Streamable HTTP** at `/mcp` (remote use) or **stdio** (local use with Claude Desktop / Claude Code).

---

## Local setup

Requires Python 3.10+ and a Kalodata API key.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # then edit .env
```

### Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `KALODATA_SECRET_KEY` | — (required) | Kalodata Open API key |
| `KALODATA_BASE_URL` | `https://staging.kalodata.com` | Use the host from your activation email for production keys |
| `KALODATA_TIMEOUT` | `30` | Request timeout in seconds |
| `KALODATA_DEFAULT_REGION` | `US` | Default `region` (set `VN` for Vietnam) |
| `KALODATA_DEFAULT_LANGUAGE` | `en-US` | Default `language` (e.g. `vi-VN`) |
| `KALODATA_DEFAULT_CURRENCY` | `USD` | Default `currency` (e.g. `VND`) |
| `KALODATA_DEFAULT_DATE_RANGE` | `last7Day` | Default `date_range` |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` or `stdio` |
| `MCP_AUTH_TOKEN` | empty | If set, HTTP clients must send `Authorization: Bearer <token>` |
| `MCP_STATELESS_HTTP` | `true` | Stateless HTTP mode (survives restarts / free-tier sleep) |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | HTTP bind address |

---

## Testing

```bash
# Offline unit tests (API mocked, no key needed)
pip install -r requirements-dev.txt
pytest -q

# Live smoke test against the real API (needs KALODATA_SECRET_KEY)
python scripts/smoke_test.py                 # default region
python scripts/smoke_test.py VN vi-VN VND    # Vietnam market
```

Run the HTTP server and call it:

```bash
python server.py

curl -s -N \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  http://localhost:8000/mcp
```

> Streamable HTTP requires `Accept: application/json, text/event-stream`; without it the server answers 406.

Visual testing with MCP Inspector:

```bash
MCP_TRANSPORT=stdio npx @modelcontextprotocol/inspector python server.py
```

---

## Using with Claude

**Claude Code (local, stdio):**

```bash
claude mcp add kalodata \
  -e KALODATA_SECRET_KEY=your_key -e MCP_TRANSPORT=stdio \
  -- python /path/to/kalodata-mcp/server.py
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kalodata": {
      "command": "python",
      "args": ["/path/to/kalodata-mcp/server.py"],
      "env": { "KALODATA_SECRET_KEY": "your_key", "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

**Remote (deployed) server:**

```bash
claude mcp add --transport http kalodata https://<your-app>.onrender.com/mcp \
  --header "Authorization: Bearer <MCP_AUTH_TOKEN>"
```

---

## Deploy to Render.com

`render.yaml` is included, so you can deploy as a **Blueprint**:

1. Push this repo to GitHub.
2. In [dashboard.render.com](https://dashboard.render.com): **New +** → **Blueprint** → connect the repo.
3. Fill in `KALODATA_SECRET_KEY` and `KALODATA_BASE_URL`. `MCP_AUTH_TOKEN` is generated automatically; copy it from the Environment tab.
4. **Apply**, wait for "Live", then test `https://<your-app>.onrender.com/mcp` with the curl command above.

> The free plan sleeps after inactivity; the first request after that can take ~30–60 s.

### Perplexity custom connector

Settings → Connectors → **+ Custom connector** → Remote, URL `https://<your-app>.onrender.com/mcp`, transport Streamable HTTP. If your client cannot send a bearer header, leave `MCP_AUTH_TOKEN` empty, but be aware that anyone with the URL can then spend your Kalodata quota.

---

## Security

- Never commit `.env` (already in `.gitignore`) or put keys in `render.yaml`.
- The Kalodata key lives only in the server environment; MCP clients never see it.
- Set `MCP_AUTH_TOKEN` for any public deployment.

---

## Credits

Forked from an original Portuguese-language project; translated to English/Vietnamese and extended.
