# TWSE 有價證券清單爬蟲

> 抽抽樂頁面顯示的「代號」與「產業別」均來自此清單。
> 來源：台灣證券交易所 ISIN 公告頁。

---

## 用途

把 TWSE 公告的上市證券清單萃取下來，產出兩份檔案供其他模組查詢：

| 輸出 | 路徑 | 消費者 |
|------|------|------|
| JSON | `backend/data/funds/symbol.json` | [lucky_aggregator.py](../../core/funds/lucky_aggregator.py) 用來補代號與產業別 |
| CSV  | `backend/data/funds/symbol.csv`  | 人工檢視 / 其他外部工具 |

---

## 模組職責

| 模組 | 角色 |
|------|------|
| [run_twse_securities.py](../../run_twse_securities.py) | CLI 入口；補 `sys.path` 後呼叫 `twse_securities.run_forever()` |
| [core/funds/twse_securities.py](../../core/funds/twse_securities.py) | 抓取、解析、寫檔、排程 |
| [core/funds/_schedule_utils.py](../../core/funds/_schedule_utils.py) | 與基金排程器共用的「下一個時刻」計算 |

---

## CLI 啟動

```
python -m backend.run_twse_securities
python backend/run_twse_securities.py
```

啟動後：

1. 立即跑一次 `fetch_and_save()`；
2. 之後依 `TWSE_SECURITIES_RUN_TIMES`（預設 `(3, 0)`、`(15, 0)`，見 [config.py](../../core/shared/config.py)）持續排程；
3. `Ctrl+C` 乾淨退出。

---

## 抓取流程

來源清單：`TWSE_SECURITIES_SOURCES`（[config.py](../../core/shared/config.py)），預設兩筆：

| market 標籤 | `strMode` | 說明 |
|------------|-----------|------|
| `上市` | `2` | TSE 上市股票（主板） |
| `上櫃` | `4` | TPEx 上櫃股票（需含此來源，否則 8299 群聯、5274 信驊、6261 鴻勁等上櫃 ETF 持股查無資料） |

| 步驟 | 函式 | 說明 |
|------|------|------|
| 1 | `_fetch_page()` | `requests.get` 帶 User-Agent，timeout 30 秒；強制以 `big5` 解碼，避免亂碼。逐一處理 `TWSE_SECURITIES_SOURCES` |
| 2 | `_extract_update_date()` | 從含「最近更新日期」的文字節點 regex 取出 `YYYY/MM/DD`；採第一個成功解析的日期 |
| 3 | `_extract_securities(tree, market)` | 解析第二個 `<table>`，自第 3 列起逐列取「代號 名稱 / 上市日期 / 產業別」，並附上 `market` 標籤 |
| 4 | `_merge_securities()` | 把各來源結果併入單一 list；同 `symbol` 衝突時保留先到者並記 warning |
| 5 | `_write_csv()` + `save_json()` | 兩份檔案以 `utf-8-sig` 覆寫；JSON 結構為 `{ update_date, data: [...] }` |

**失敗保護**：
- 單一來源 fetch 失敗時 log exception 並跳過，其餘來源仍正常合併。
- 解析不到任何證券（**所有來源都失敗**）時不寫檔，避免覆蓋既有有效資料（`fetch_and_save()` 回傳 `False`）。

---

## 輸出格式

`symbol.json`：

```json
{
  "update_date": "2026/05/23",
  "data": [
    { "symbol": "1101", "name": "台泥", "listing_date": "1962/02/09", "industry": "水泥工業", "market": "上市" },
    { "symbol": "8299", "name": "群聯", "listing_date": "2011/06/27", "industry": "半導體業", "market": "上櫃" }
  ]
}
```

`symbol.csv` 欄位順序固定為 `_CSV_FIELDS`：`symbol, name, listing_date, industry, market`。

> `market` 欄位目前不被 [lucky_aggregator.py](../../core/funds/lucky_aggregator.py) 使用，但保留以便未來在前端區分「上市 / 上櫃」徽章。

---

## 排程時刻調整

修改 [config.py](../../core/shared/config.py) 的 `TWSE_SECURITIES_RUN_TIMES`：

```python
TWSE_SECURITIES_RUN_TIMES: Final[tuple[tuple[int, int], ...]] = (
    (3, 0),
    (15, 0),
)
```

時刻計算邏輯與基金排程器共用，見 [funds_pipeline.md](funds_pipeline.md#排程時刻調整)。

---

## 與抽抽樂的串接

[lucky_aggregator.py](../../core/funds/lucky_aggregator.py) `_load_symbol_lookup()` 會：

1. 讀 `symbol.json`；
2. 以「股票名稱」為 key 建 `dict[name, {symbol, industry}]`；
3. 比對前先 `_normalize_stock_name()`（去除尾端 `*`）以容忍狀態標記差異。

`symbol.json` 不存在或解析失敗時：lookup 為空 → 所有股票的 `symbol` / `industry` 均為 `null`，但抽抽樂功能仍可運作。
