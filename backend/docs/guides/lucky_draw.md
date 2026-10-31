# 抽抽樂後端

> 把已寫入磁碟的 ETF 成分股聚合成「可抽取股票池」，供前端隨機抽取。
> API 規格詳見 [api_docs.md `GET /api/funds/latest`](../api_docs.md#get-apifundslatest)。
> 流程圖見 [architecture/lucky_draw_sequence.md](../architecture/lucky_draw_sequence.md)。

---

## 設計目標

| 目標 | 對應做法 |
|------|---------|
| 路由層輕薄 | 路由不直接讀檔，全部委派給 aggregator |
| 同名股票合併 | 以「股票名稱」（去 `*` 後）為聚合 key |
| 標記容忍 | `國巨*`、`貿聯-KY` 等狀態標記在比對前先 `_normalize_stock_name()` |
| 部分缺檔不致命 | 5 檔 ETF 中只要任一支有資料即可成立股票池 |
| TWSE 查無不致命 | `symbol` / `industry` 缺失時以 `null` 回傳，前端自行降階顯示 |
| 排序穩定 | 股票池依 `name` 升冪排序，方便前端 debug / 比對 |

---

## 模組職責

| 模組 | 角色 |
|------|------|
| [routers/funds.py](../../routers/funds.py) | `APIRouter(prefix="/api/funds")` 與 `get_latest_lucky_pool()` 路由 |
| [core/funds/lucky_aggregator.py](../../core/funds/lucky_aggregator.py) | 找日期資料夾、讀 ETF JSON、讀 symbol.json、輸出 `FundsLuckyResponse` |
| [schemas/funds_lucky.py](../../schemas/funds_lucky.py) | `DrawSource` / `DrawableStock` / `FundsLuckyResponse` Pydantic schema |
| [main.py](../../main.py) | FastAPI app；`include_router(funds_router.router)` |

---

## 主要函式

### `find_latest_dated_dir(base, required_codes)`

從 `base` 開始遞迴搜尋 `yyyy/mm/dd` 結構，命中第一個含 `<code>.json`（其中 `code` 來自 `required_codes`）的資料夾即停止。

| 屬性 | 內容 |
|------|------|
| 排序策略 | 年→月→日皆字典序倒排（最大者優先） |
| `required_codes` 預設 | `tuple(entry.code for entry in CRAWLERS)`，與 registry 同步 |
| 找不到時 | 回傳 `None`，由路由層轉成 HTTP 404 |

### `_normalize_stock_name(raw)`

去除尾端 `*` 與兩側空白。例：

| 原始 | 正規化 |
|------|--------|
| `"國巨*"` | `"國巨"` |
| `" 台積電 "` | `"台積電"` |
| `"貿聯-KY"` | `"貿聯-KY"`（保留，因 `symbol.json` 也是這個名字） |

### `_load_snapshots(latest_dir)`

讀取最新資料夾下所有「已註冊」ETF 的快照。檔案缺失或解析失敗只記 log、跳過，不終止流程。

### `_load_symbol_lookup()`

讀取 `FUNDS_DATA_ROOT/symbol.json`，建立 `dict[name, {symbol, industry}]`。檔案不存在時回傳空 dict，並 log warning。

### `build_lucky_response(base, today)`

主入口。流程：

1. 呼叫 `find_latest_dated_dir()`；找不到 → 回傳 `None`。
2. `_load_snapshots()`；零成功 → 回傳 `None`。
3. `_load_symbol_lookup()`；
4. 對每支 holding 算正規化名稱、建立 `DrawSource`；
5. 同名則 append 到既有 `DrawableStock.sources`，否則新建一筆並查 symbol lookup；
6. 依 `name` 升冪輸出 `FundsLuckyResponse`。

`today` 參數目前未使用，預留給未來「指定日期回放」功能。

---

## 與其他模組的耦合點

| 變動點 | 須同步調整 |
|--------|----------|
| 新增 ETF 爬蟲 | 只需動 [registry.py](../../core/funds/registry.py)。`required_codes` 預設由 CRAWLERS 推導，aggregator 不必改 |
| `StockPriceSnapshot` 結構變動 | 同步 [schemas/stock_price.py](../../schemas/stock_price.py)；aggregator 透過 `model_validate` 解析 |
| `symbol.json` 結構變動 | 同步 [twse_securities.py](../../core/funds/twse_securities.py) 與 aggregator 的 `_load_symbol_lookup()` |
| API 回傳欄位變動 | 同步 [schemas/funds_lucky.py](../../schemas/funds_lucky.py)、[api_docs.md](../api_docs.md)、前端 [types/funds.ts](../../../frontend/src/types/funds.ts) 與 [services/funds.ts](../../../frontend/src/services/funds.ts) |

---

## 已知邊界情境

| 情境 | 行為 |
|------|------|
| 完全無資料夾 | 路由回 404 `"尚未抓取到任何基金資料；請先執行爬蟲。"` |
| 最新日期僅部分 ETF | 部分 ETF 缺檔記 warning；其餘正常聚合 |
| `symbol.json` 不存在 | 全體股票 `symbol=null, industry=null`；功能仍可用 |
| 同一 ETF 內出現重複股票名 | 目前不做去重；聚合後該股票會有多筆同 `etf_code` 的 source（爬蟲端應確保唯一） |
| 股票名稱完全為空 | 跳過該筆，不進入股票池 |
