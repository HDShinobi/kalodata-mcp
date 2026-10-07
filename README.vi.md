# Kalodata MCP Server (Phân tích TikTok Shop)

[English](README.md) | **Tiếng Việt**

Server MCP (**Model Context Protocol**) viết bằng Python với SDK chính thức (`FastMCP`), bọc **Kalodata Open API**. Giúp trợ lý AI và agent (Claude, Perplexity, Cursor, …) nghiên cứu thị trường TikTok Shop: ngách, sản phẩm thắng, creator, video viral, shop và livestream.

---

## Các tool

| Đối tượng  | Bảng xếp hạng      | Chi tiết             |
|------------|--------------------|----------------------|
| Danh mục   | `category_rank`    | `category_detail`    |
| Sản phẩm   | `product_rank`     | `product_detail`     |
| Creator    | `creator_rank`     | `creator_detail`     |
| Video      | `video_rank`       | `video_detail`       |
| Shop       | `shop_rank`        | `shop_detail`        |
| Livestream | `livestream_rank`  | `livestream_detail`  |

Luồng thường dùng: gọi tool `*_rank`, lấy ID trong kết quả, truyền vào tool `*_detail` tương ứng.

Tham số chung (đều tùy chọn, mặc định lấy từ env):

- `region`: mã thị trường, ví dụ `US`, `VN`, `ID`, `TH`, `MY`, `PH`, `GB`
- `language`: ví dụ `en-US`, `vi-VN`
- `currency`: ví dụ `USD`, `VND`
- `date_range`: ví dụ `last7Day`
- Tool rank nhận thêm `sort_field` (mặc định `{"field": "revenue", "type": "DESC"}`), `page_number` và `page_size`.

Transport: **Streamable HTTP** tại `/mcp` (dùng từ xa) hoặc **stdio** (dùng local với Claude Desktop / Claude Code).

---

## Cài đặt local

Cần Python 3.10+ và API key Kalodata.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # rồi sửa .env
```

### Cấu hình (`.env`)

| Biến | Mặc định | Mô tả |
|---|---|---|
| `KALODATA_SECRET_KEY` | — (bắt buộc) | API key Kalodata Open API |
| `KALODATA_BASE_URL` | `https://staging.kalodata.com` | Key production thì dùng host trong email kích hoạt |
| `KALODATA_TIMEOUT` | `30` | Timeout mỗi request (giây) |
| `KALODATA_DEFAULT_REGION` | `US` | `region` mặc định (đặt `VN` cho Việt Nam) |
| `KALODATA_DEFAULT_LANGUAGE` | `en-US` | `language` mặc định (ví dụ `vi-VN`) |
| `KALODATA_DEFAULT_CURRENCY` | `USD` | `currency` mặc định (ví dụ `VND`) |
| `KALODATA_DEFAULT_DATE_RANGE` | `last7Day` | `date_range` mặc định |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` hoặc `stdio` |
| `MCP_AUTH_TOKEN` | rỗng | Nếu đặt, client HTTP phải gửi `Authorization: Bearer <token>` |
| `MCP_STATELESS_HTTP` | `true` | Chế độ HTTP stateless (không lỗi khi server restart / ngủ) |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Địa chỉ lắng nghe HTTP |

---

## Kiểm thử

```bash
# Unit test offline (mock API, không cần key)
pip install -r requirements-dev.txt
pytest -q

# Smoke test với API thật (cần KALODATA_SECRET_KEY)
python scripts/smoke_test.py                 # region mặc định
python scripts/smoke_test.py VN vi-VN VND    # thị trường Việt Nam
```

Chạy server HTTP và gọi thử:

```bash
python server.py

curl -s -N \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  http://localhost:8000/mcp
```

> Streamable HTTP bắt buộc header `Accept: application/json, text/event-stream`; thiếu thì server trả 406.

Test bằng giao diện MCP Inspector:

```bash
MCP_TRANSPORT=stdio npx @modelcontextprotocol/inspector python server.py
```

---

## Dùng với Claude

**Claude Code (local, stdio):**

```bash
claude mcp add kalodata \
  -e KALODATA_SECRET_KEY=key_cua_ban -e MCP_TRANSPORT=stdio \
  -- python /duong/dan/kalodata-mcp/server.py
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kalodata": {
      "command": "python",
      "args": ["/duong/dan/kalodata-mcp/server.py"],
      "env": { "KALODATA_SECRET_KEY": "key_cua_ban", "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

**Server đã deploy (từ xa):**

```bash
claude mcp add --transport http kalodata https://<app-cua-ban>.onrender.com/mcp \
  --header "Authorization: Bearer <MCP_AUTH_TOKEN>"
```

---

## Deploy lên Render.com

Repo đã có `render.yaml`, deploy dạng **Blueprint**:

1. Push repo lên GitHub.
2. Vào [dashboard.render.com](https://dashboard.render.com): **New +** → **Blueprint** → kết nối repo.
3. Điền `KALODATA_SECRET_KEY` và `KALODATA_BASE_URL`. `MCP_AUTH_TOKEN` được sinh tự động; copy ở tab Environment.
4. **Apply**, đợi trạng thái "Live", rồi test `https://<app-cua-ban>.onrender.com/mcp` bằng lệnh curl ở trên.

> Gói free sẽ ngủ khi không có request; request đầu tiên sau đó mất khoảng 30–60 giây.

### Connector tùy chỉnh trên Perplexity

Settings → Connectors → **+ Custom connector** → Remote, URL `https://<app-cua-ban>.onrender.com/mcp`, transport Streamable HTTP. Nếu client không gửi được header bearer, để trống `MCP_AUTH_TOKEN` — nhưng khi đó ai có URL cũng dùng được quota Kalodata của bạn.

---

## Bảo mật

- Không commit `.env` (đã có trong `.gitignore`) và không ghi key vào `render.yaml`.
- Key Kalodata chỉ nằm trong env của server; client MCP không bao giờ thấy.
- Luôn đặt `MCP_AUTH_TOKEN` khi deploy public.

---

## Nguồn

Fork từ một project gốc viết bằng tiếng Bồ Đào Nha; đã dịch sang tiếng Anh/tiếng Việt và mở rộng.
