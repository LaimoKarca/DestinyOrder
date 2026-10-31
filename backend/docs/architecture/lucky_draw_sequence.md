# 抽抽樂 API 互動循序圖

> 對應實作：[lucky_draw.md](../guides/lucky_draw.md)、[api_docs.md `GET /api/funds/latest`](../api_docs.md#get-apifundslatest)。
> 前端動畫流程見 [frontend_integration.md](../../../frontend/docs/guides/frontend_integration.md)。

---

## 正常流程（200）

```mermaid
sequenceDiagram
    autonumber
    participant U as 使用者瀏覽器
    participant V as Vite Dev Server<br/>(localhost:5173)
    participant F as LuckyDraw.vue
    participant S as services/funds.ts
    participant FAPI as FastAPI<br/>(127.0.0.1:8000)
    participant R as routers/funds.py
    participant A as lucky_aggregator.py
    participant FS as backend/data/funds/

    U->>V: GET /
    V-->>U: index.html + bundle
    U->>F: onMounted()
    F->>S: fetch_latest_funds()
    S->>V: fetch('/api/funds/latest')
    V->>FAPI: proxy 轉發
    FAPI->>R: get_latest_lucky_pool()
    R->>A: build_lucky_response()
    A->>FS: find_latest_dated_dir()
    FS-->>A: 2026/05/23/
    A->>FS: read 0050.json … 00981A.json
    FS-->>A: 5 份 StockPriceSnapshot
    A->>FS: read symbol.json
    FS-->>A: TWSE 證券查表
    A-->>R: FundsLuckyResponse
    R-->>FAPI: 200 + JSON
    FAPI-->>V: 200 + JSON
    V-->>S: Response
    S-->>F: payload
    F-->>F: pool.value = payload.stocks
    F-->>U: 顯示「等待開獎」狀態

    Note over U,F: 使用者點擊「開始抽抽」
    U->>F: click draw()
    F-->>F: 1.4 秒滾動動畫<br/>每 tick pick_random_stock
    F-->>U: 揭曉命運標的
```

---

## 無資料時（404）

```mermaid
sequenceDiagram
    autonumber
    participant F as LuckyDraw.vue
    participant S as services/funds.ts
    participant R as routers/funds.py
    participant A as lucky_aggregator.py
    participant FS as backend/data/funds/

    F->>S: fetch_latest_funds()
    S->>R: GET /api/funds/latest
    R->>A: build_lucky_response()
    A->>FS: find_latest_dated_dir()
    FS-->>A: None
    A-->>R: None
    R-->>S: 404<br/>{ "detail": "尚未抓取到任何基金資料；請先執行爬蟲。" }
    S-->>F: throw Error(detail)
    F-->>F: error.value = e.message
    Note over F: UI 顯示錯誤狀態與排查提示
```

---

## 重點說明

| 步驟 | 對應程式碼 |
|------|-----------|
| `proxy 轉發` | [frontend/vite.config.ts](../../../frontend/vite.config.ts) `server.proxy['/api']` → `http://127.0.0.1:8000` |
| `pick_random_stock` | [frontend/src/services/funds.ts](../../../frontend/src/services/funds.ts) |
| 1.4 秒滾動動畫 | [frontend/src/views/LuckyDraw.vue](../../../frontend/src/views/LuckyDraw.vue) `draw()` |
| 路由 404 訊息 | [backend/routers/funds.py](../../routers/funds.py) `HTTPException(status_code=404, detail=...)` |
