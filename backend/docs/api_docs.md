# DestinyOrder Backend — API 文件

> **現行完整安裝、合成示範資料初始化與部署主指南請以專案根目錄 [`README.md`](../../README.md) 與 [`docs/deployment.md`](../../docs/deployment.md) 為準。**
> Base URL：`http://127.0.0.1:8000`（開發預設）
> 啟動入口：[backend/main.py](../main.py)
> 推薦啟動方式（於專案根目錄）：`python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`（或直接執行 `python backend/main.py`）

---

## 目錄

| 群組 | 端點 | 方法 | 說明 |
|------|------|------|------|
| meta | [`/api/health`](#get-apihealth) | GET | 健康檢查 |
| funds | [`/api/funds/latest`](#get-apifundslatest) | GET | 取得最新日期的抽抽樂股票池 |
| funds | [`/api/funds/by_etf`](#get-apifundsby_etf) | GET | 取得最新日期下，依 ETF 分組的成分股明細 |

---

## meta

### `GET /api/health`

回傳目前服務是否存活；無任何商業邏輯。

| 項目 | 內容 |
|------|------|
| 路徑 | `/api/health` |
| 方法 | `GET` |
| 認證 | 無 |
| 程式碼 | [backend/main.py](../main.py) `health_check()` |

**回應 200**

```json
{ "status": "ok" }
```

---

## funds

### `GET /api/funds/latest`

回傳「`backend/data/funds/` 之下最新日期資料夾」所聚合而成的抽抽樂股票池。

| 項目 | 內容 |
|------|------|
| 路徑 | `/api/funds/latest` |
| 方法 | `GET` |
| 認證 | 無 |
| 程式碼 | [backend/routers/funds.py](../routers/funds.py) `get_latest_lucky_pool()` |
| 聚合邏輯 | [backend/core/funds/lucky_aggregator.py](../core/funds/lucky_aggregator.py) `build_lucky_response()` |
| Response Schema | [backend/schemas/funds_lucky.py](../schemas/funds_lucky.py) `FundsLuckyResponse` |

**行為**

1. 從 `FUNDS_DATA_ROOT`（`backend/data/funds/`）開始遞迴搜尋符合 `yyyy/mm/dd` 結構的最新資料夾，命中第一個含有任一已註冊 ETF JSON 的資料夾即停止。
2. 讀取該資料夾下所有已註冊 ETF 的快照（見 [registry.py](../core/funds/registry.py) `CRAWLERS`）。
3. 比對 `backend/data/funds/symbol.json` 補上股票代號與產業別（名稱尾端 `*` 等狀態標記會先去除再比對）。
4. 以「股票名稱」為 key 聚合，輸出可抽取股票池。

**回應 200 — `FundsLuckyResponse`**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | `string` | 來源資料夾相對路徑，例：`"2026/05/23"` |
| `etf_codes` | `string[]` | 此次實際被聚合進來的 ETF 代號列表 |
| `stocks` | `DrawableStock[]` | 可抽取股票池，依 `name` 升冪排序 |

`DrawableStock`：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `name` | `string` | 股票名稱，已去除 `*` 等狀態尾綴 |
| `symbol` | `string \| null` | TWSE 證券代號；`symbol.json` 查無時為 `null` |
| `industry` | `string \| null` | TWSE 公告的產業別；查無時為 `null` |
| `sources` | `DrawSource[]` | 哪幾檔 ETF 持有此股 |

`DrawSource`：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `etf_code` | `string` | ETF 代號（如 `"0050"`、`"00981A"`） |
| `etf_name` | `string` | ETF 完整名稱（如 `"元大台灣卓越50基金"`） |
| `weight` | `string` | 該股在此 ETF 內的權重，保留原始字串（含 `%`） |

**回應範例**

```json
{
  "date": "2026/05/23",
  "etf_codes": ["0050", "006208", "009816", "00403A", "00981A"],
  "stocks": [
    {
      "name": "台積電",
      "symbol": "2330",
      "industry": "半導體業",
      "sources": [
        { "etf_code": "0050",   "etf_name": "元大台灣卓越50基金", "weight": "61.06%" },
        { "etf_code": "006208", "etf_name": "富邦台50",           "weight": "59.3958%" },
        { "etf_code": "009816", "etf_name": "凱基台灣TOP50基金",  "weight": "41.36%" },
        { "etf_code": "00403A", "etf_name": "主動統一升級50",     "weight": "16.83%" },
        { "etf_code": "00981A", "etf_name": "主動統一台股增長",   "weight": "9.66%" }
      ]
    }
  ]
}
```

**回應 404**

當 `FUNDS_DATA_ROOT` 之下找不到任何符合條件的日期資料夾、或最新資料夾內所有 ETF 快照皆讀取失敗時：

```json
{ "detail": "尚未抓取到任何基金資料；請先執行爬蟲。" }
```

排查：公開版本庫預設不含真實爬蟲資料，請先於專案根目錄執行 `python scripts/seed_demo_data.py`（或 `python -m backend.scripts.seed_demo_data`）產生 `2000/01/03` 合成示範資料後再重試；若為自行啟用選用爬蟲之環境（需先確認符合各官方網站服務條款），則可確認 [run_scheduler.py](../run_scheduler.py) 是否已於 `backend/data/funds/<yyyy>/<mm>/<dd>/` 下產出有效 JSON。

---

### `GET /api/funds/by_etf`

回傳「`backend/data/funds/` 之下最新日期資料夾」之下，**依 ETF 分組**的成分股明細，並補上每檔 ETF 的官方來源網址；供前端「權重查詢」頁面使用。

| 項目 | 內容 |
|------|------|
| 路徑 | `/api/funds/by_etf` |
| 方法 | `GET` |
| 認證 | 無 |
| 程式碼 | [backend/routers/funds.py](../routers/funds.py) `get_by_etf_breakdown()` |
| 聚合邏輯 | [backend/core/funds/etf_aggregator.py](../core/funds/etf_aggregator.py) `build_by_etf_response()` |
| Response Schema | [backend/schemas/funds_etf.py](../schemas/funds_etf.py) `FundsByEtfResponse` |

**行為**

1. 找最新含資料的日期資料夾（與 `/latest` 共用 `find_latest_dated_dir()`）。
2. 讀取該資料夾下所有已註冊 ETF 快照（與 `/latest` 共用 `_load_snapshots()`）。
3. 比對 `symbol.json` 補上 `symbol`；持股順序保留原始 JSON 順序（通常為權重由大到小）。
4. 依 `CRAWLERS` 註冊順序輸出（讓前端下拉選單順序穩定）。
5. 每筆 ETF 的 `source_url` 來自 [registry.py](../core/funds/registry.py) `CrawlerEntry.source_url`，新增爬蟲時記得提供此欄位。

**回應 200 — `FundsByEtfResponse`**

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | `string` | 來源資料夾相對路徑，例：`"2026/05/23"` |
| `etfs` | `EtfDetail[]` | 各檔 ETF 完整明細，依註冊順序排列 |

`EtfDetail`：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `code` | `string` | ETF 代號 |
| `name` | `string` | ETF 完整名稱 |
| `update_time` | `string` | 該檔 ETF 自身公告的資料日期（讀自 snapshot 的 `update_time`） |
| `source_url` | `string` | 該檔 ETF 的官方資料來源網址 |
| `holdings` | `EtfHolding[]` | 持股明細（保留原始順序） |

`EtfHolding`：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `name` | `string` | 股票名稱，已去除 `*` 等狀態尾綴 |
| `symbol` | `string \| null` | TWSE 證券代號；查無時為 `null` |
| `weight` | `string` | 該股在此 ETF 內的權重，保留原始字串（含 `%`） |

**回應範例**

```json
{
  "date": "2026/05/23",
  "etfs": [
    {
      "code": "00403A",
      "name": "主動統一升級50",
      "update_time": "2026/05/22",
      "source_url": "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=63YTW&tabName=basic#",
      "holdings": [
        { "name": "台積電", "symbol": "2330", "weight": "16.83%" },
        { "name": "欣興", "symbol": "3037", "weight": "4.63%" }
      ]
    }
  ]
}
```

**回應 404**

行為與 `/api/funds/latest` 相同，回傳：

```json
{ "detail": "尚未抓取到任何基金資料；請先執行爬蟲。" }
```

---

## CORS

開發階段於 [backend/main.py](../main.py) 開啟 `CORSMiddleware`，允許下列 origin 直接呼叫：

- `http://localhost:5173`
- `http://127.0.0.1:5173`

僅允許 `GET` 方法。正式部署時應收斂 `allow_origins` 為實際前端 origin 或關閉 CORS（改由反向代理處理）。

預設前端 Vite dev server 透過 `vite.config.ts` 的 proxy 把 `/api/*` 轉發到本後端，CORS 在該路徑下不會被觸發；以上 CORS 設定是「不走 proxy 時的雙保險」。
