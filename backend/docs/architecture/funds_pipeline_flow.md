# 基金資料管線流程圖

> 對應實作：[funds_pipeline.md](../guides/funds_pipeline.md)、[twse_securities.md](../guides/twse_securities.md)、[lucky_draw.md](../guides/lucky_draw.md)。

---

## 1. ETF 成分股爬蟲與儲存

```mermaid
flowchart TD
    A[python -m backend.run_scheduler] --> B[scheduler.run_forever]
    B --> C{首次啟動?}
    C -- 是 --> D[orchestrator.run_all]
    C -- 否 --> E[seconds_until_next_run<br/>由 DAILY_RUN_TIMES 推算]
    E -- time.sleep --> D
    D --> F[逐一執行 CRAWLERS]
    F --> G1[yuanta_0050.fetch]
    F --> G2[fubon_006208.fetch]
    F --> G3[kgi_009816.fetch]
    F --> G4[uni_00403a.fetch]
    F --> G5[uni_00981a.fetch]
    G1 & G2 & G3 & G4 & G5 --> H{snapshot is None<br/>or raised?}
    H -- 失敗 --> I[logger.exception<br/>跳過該支]
    H -- 成功 --> J[save_json<br/>backend/data/funds/yyyy/mm/dd/<code>.json]
    I & J --> K[batch done log]
    K --> E
```

**重點**：

- 同一天多次執行寫進同一個 `yyyy/mm/dd` 資料夾，後者覆寫前者。
- 任何單支 crawler 拋例外都被 `orchestrator._run_single()` 接住，不影響其餘 crawler。

---

## 2. TWSE 證券清單爬蟲與儲存

```mermaid
flowchart TD
    A[python -m backend.run_twse_securities] --> B[twse_securities.run_forever]
    B --> C[fetch_and_save]
    C --> D[requests.get<br/>TWSE_SECURITIES_URL]
    D -- big5 decode --> E[lxml.html.fromstring]
    E --> F[_extract_update_date]
    E --> G[_extract_securities<br/>table 2 第 3 列起]
    G --> H{securities 為空?}
    H -- 是 --> I[skip write<br/>logger.warning]
    H -- 否 --> J[_write_csv -> symbol.csv]
    H -- 否 --> K[save_json -> symbol.json]
    I & J & K --> L[seconds_until_next_run<br/>由 TWSE_SECURITIES_RUN_TIMES 推算]
    L -- time.sleep --> C
```

**重點**：

- 解析失敗時不覆寫，保留前一份有效資料。
- `symbol.json` 是抽抽樂查代號 / 產業別的唯一來源。

---

## 3. 抽抽樂聚合（讀取端）

```mermaid
flowchart TD
    A[/GET /api/funds/latest/] --> B[get_latest_lucky_pool]
    B --> C[build_lucky_response]
    C --> D[find_latest_dated_dir<br/>遞迴搜尋 yyyy/mm/dd]
    D --> E{找到?}
    E -- 否 --> F[return None]
    E -- 是 --> G[_load_snapshots<br/>逐個讀 CRAWLERS 中的 code.json]
    G --> H{至少一支成功?}
    H -- 否 --> F
    H -- 是 --> I[_load_symbol_lookup<br/>讀 symbol.json]
    I --> J[逐 holding 聚合<br/>同名合併 sources]
    J --> K[依 name 升冪排序]
    K --> L[FundsLuckyResponse]
    F --> M[HTTPException 404]
    L --> N[200 JSON]
```

---

## 名詞對照表

| 流程圖節點 | 程式碼位置 |
|------------|-----------|
| `scheduler.run_forever` | [core/funds/scheduler.py](../../core/funds/scheduler.py) `run_forever()` |
| `orchestrator.run_all` | [core/funds/orchestrator.py](../../core/funds/orchestrator.py) `run_all()` |
| `seconds_until_next_run` | [core/funds/_schedule_utils.py](../../core/funds/_schedule_utils.py) |
| `save_json` | [core/shared/json_storage.py](../../core/shared/json_storage.py) |
| `fetch_and_save` | [core/funds/twse_securities.py](../../core/funds/twse_securities.py) |
| `build_lucky_response` | [core/funds/lucky_aggregator.py](../../core/funds/lucky_aggregator.py) |
| `find_latest_dated_dir` | 同上 |
| `_load_snapshots` / `_load_symbol_lookup` | 同上 |
| `get_latest_lucky_pool` | [routers/funds.py](../../routers/funds.py) |
