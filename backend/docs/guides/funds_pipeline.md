# 基金成分股爬蟲流程

> 本文件涵蓋「ETF 成分股」從爬蟲、排程到磁碟儲存的完整鏈路。
> TWSE 證券代號清單（`symbol.json`）為獨立流程，見 [twse_securities.md](twse_securities.md)。
> 抽抽樂 API 如何讀取本文件產出的 JSON，見 [lucky_draw.md](lucky_draw.md)。

---

## 整體架構

```
run_scheduler.py  ──►  scheduler.run_forever()
                            │  每日 DAILY_RUN_TIMES 觸發
                            ▼
                       orchestrator.run_all()
                            │  逐一呼叫 CRAWLERS 中的 fetch()
                            ▼
        ┌──────────┬──────────┬──────────┬──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼          ▼
   yuanta_0050 fubon_006208 kgi_009816 uni_00403a uni_00981a   …新爬蟲
        │          │          │          │          │
        └──────────┴────┬─────┴──────────┴──────────┘
                       ▼
            StockPriceSnapshot (Pydantic)
                       │
                       ▼
           save_json → backend/data/funds/<yyyy>/<mm>/<dd>/<code>.json
```

---

## 模組職責

| 模組 | 角色 |
|------|------|
| [run_scheduler.py](../../run_scheduler.py) | CLI 入口；補 `sys.path` 後呼叫 `scheduler.run_forever()` |
| [core/funds/scheduler.py](../../core/funds/scheduler.py) | 常駐主迴圈；啟動先跑一次，之後按 `DAILY_RUN_TIMES` 重複 |
| [core/funds/_schedule_utils.py](../../core/funds/_schedule_utils.py) | 計算「距下一個排定時刻」的等待秒數，與時刻日誌格式化 |
| [core/funds/orchestrator.py](../../core/funds/orchestrator.py) | 依序執行 `CRAWLERS` 中的所有 fetch，並把 snapshot 寫入磁碟 |
| [core/funds/registry.py](../../core/funds/registry.py) | 所有爬蟲的中央註冊表 `CRAWLERS` |
| [core/funds/crawlers/](../../core/funds/crawlers/) | 各 ETF 的爬蟲實作（playwright/HTTP） |
| [core/funds/_dev_runner.py](../../core/funds/_dev_runner.py) | 單一 crawler 獨立執行 helper（測試/偵錯用） |
| [core/shared/json_storage.py](../../core/shared/json_storage.py) | `save_json()` 與 `build_dated_dir()` 共用工具 |
| [schemas/stock_price.py](../../schemas/stock_price.py) | `Holding` / `StockPriceSnapshot` Pydantic schema |

---

## CLI 啟動方式

### 1. 排程器（常駐）

```
python -m backend.run_scheduler
python backend/run_scheduler.py
```

兩種寫法等效。啟動後：

1. 立即跑一次 `orchestrator.run_all()`；
2. 之後依 `DAILY_RUN_TIMES`（見 [config.py](../../core/shared/config.py)）持續排程；
3. `Ctrl+C` 乾淨退出（`run_scheduler.py` 捕捉 `KeyboardInterrupt`）。

### 2. 單一爬蟲（偵錯）

每支 crawler 模組本身可單獨執行，結果以 JSON 寫到 stdout：

```
python -m backend.core.funds.crawlers.yuanta_0050
python -m backend.core.funds.crawlers.yuanta_0050 > out.json
```

> 邏輯定義於 [_dev_runner.py](../../core/funds/_dev_runner.py) `run_crawler_standalone()`，stdout 純 JSON、stderr 純 log，可安全用 `>` 分流。

---

## 資料儲存約定

| 約定 | 說明 |
|------|------|
| 編碼 | 一律 `utf-8-sig`（見 [config.py](../../core/shared/config.py) `ENCODING`） |
| 路徑來源 | 一律從 [config.py](../../core/shared/config.py) 取 `FUNDS_DATA_ROOT`，禁止硬編碼字串 |
| 日期分層 | `FUNDS_DATA_ROOT/<yyyy>/<mm>/<dd>/<code>.json` |
| 寫入策略 | 同日多次執行 **覆寫** 同一個資料夾下的 `<code>.json`；保留歷史日資料夾 |
| 失敗隔離 | 單一 crawler 拋例外不影響其餘 crawler（orchestrator `_run_single()` 內 `try/except`） |
| 排程器例外 | `scheduler.run_forever()` 不再吃掉 `orchestrator` 內單支爬蟲的失敗，依賴 logger 留下完整 traceback |

### 範例輸出

`backend/data/funds/2026/05/23/0050.json`：

```json
{
    "code": "0050",
    "name": "元大台灣卓越50基金",
    "nav": "97.32",
    "change_percent": "+2.02%",
    "update_time": "2026/05/22",
    "holdings": [
        { "name": "台積電", "weight": "61.06%" }
    ]
}
```

對應 schema：[StockPriceSnapshot](../../schemas/stock_price.py)。

---

## 新增爬蟲

1. 在 [core/funds/crawlers/](../../core/funds/crawlers/) 建立 `xxx_<code>.py`，匯出：
   - `CODE: Final[str]`
   - `NAME: Final[str]`
   - `fetch() -> StockPriceSnapshot | None`
2. 在 [core/funds/crawlers/__init__.py](../../core/funds/crawlers/__init__.py) 暴露模組。
3. 在 [core/funds/registry.py](../../core/funds/registry.py) 的 `CRAWLERS` tuple 增加一筆 `CrawlerEntry`。
4. orchestrator、scheduler、抽抽樂 API **不需任何修改** 即會自動納入。
5. 同步更新本文件「模組職責」表與 [lucky_draw.md](lucky_draw.md) 的 ETF 清單。
6. 同步更新 [架構流程圖](../architecture/funds_pipeline_flow.md) 的爬蟲分支節點。

---

## 排程時刻調整

修改 [config.py](../../core/shared/config.py) 的 `DAILY_RUN_TIMES`：

```python
DAILY_RUN_TIMES: Final[tuple[tuple[int, int], ...]] = (
    (8, 30),
    (15, 0),
    ...
)
```

`(0, 0)` 同時代表「今日 00:00」與「24:00」——當所有時刻皆已過，自然遞延到隔日最早時刻。
此邏輯定義於 [_schedule_utils.py](../../core/funds/_schedule_utils.py) `seconds_until_next_run()`。

---

## 注意事項

- **playwright** 是多數爬蟲的執行核心，須先 `playwright install` 安裝瀏覽器二進位。
- 各爬蟲走 XPath 鎖定 DOM，**目標網站改版時很可能整支失效**；請優先檢查 crawler 內的 `_*_XPATH` 常數。
- `text_cleaning.py` 集中處理「漲跌幅正規化」與「括號剝除」等共用清洗邏輯，新爬蟲若有類似需求請優先重用。
