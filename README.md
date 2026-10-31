# DestinyOrder — 台股 ETF 命定抽抽樂

**DestinyOrder** 是一個結合台股被動市值型與主動式 ETF 成分股候選池的隨機抽選與權重檢視工具。透過「命定抽抽樂」與「命定拉霸機」兩種互動介面，協助研究人員與一般觀察者跳脫單一選股確認偏誤，快速檢視五檔台股代表性 ETF（`0050`、`006208`、`009816`、`00403A`、`00981A`）的共同持股、產業分布與權重結構。

- **問題回報與功能建議**：<https://github.com/LaimoKarca/DestinyOrder/issues>
- **開源授權條款**：本版本庫公開之自有原創內容採用 [**MIT License**](./LICENSE)（`Copyright (c) 2026 LaimoKarca`）；第三方圖示、鷹架與相依套件保留其各自原始授權條款，金融資料與已排除之本機資產限制請參閱 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)。

---

## 重要免責聲明（非投資建議）

> **本專案與網站所展示之所有資訊（包含合成示範資料與任何 ETF 成分股、權重、產業分類或隨機抽選結果）僅供程式開發、學術研究與教育展示用途，絕不構成任何形式之投資建議、買賣推薦、招攬或收益保證。**
>
> 金融市場具備高度波動風險，任何投資決策皆應由使用者自行查核發行商與主管機關官方公告，並自負一切投資盈虧責任。

---

## 主要功能與六大路由

1. **命定抽抽樂（`/`）**：
   - 支援依五檔 ETF 多選篩選候選池，一鍵隨機抽選單一成分股，呈現代號、名稱、產業別與各收錄 ETF 之權重標籤。
   - 空篩選時自動停用抽選按鈕防呆。
2. **命定拉霸機（`/slot`）**：
   - 三軸滾輪視覺化互動，搭配內建保底機制（連續未中達上限後下一輪必定三軸連線命中），並於行動裝置自動鎖定頁面捲動以維持單屏操作體驗。
3. **五檔 ETF 成分股一覽（`/holdings`）**：
   - 彙整候選池所有不重複個股，預設依「共同持有 ETF 檔數」由高至低排序，支援代號/名稱即時搜尋、產業別單選與 ETF 多重交集篩選。
4. **各 ETF 權重查詢（`/weights`）**：
   - 依單一 ETF（`0050`、`006208`、`009816`、`00403A`、`00981A`）檢視完整成分股權重明細、資料更新日期與發行商官方來源連結。
5. **關於本站（`/about`）**：
   - 說明隨機漫步假說、效率市場假說、SPIVA 報告背景與行為經濟學遊戲化設計理念。
6. **常見問題（`/faq`）**：
   - 解答五檔被動/主動式 ETF 選樣原因、資料更新頻率、隱私聲明與問題回饋管道。

---

## 技術架構

- **後端（Backend）**：
  - **FastAPI + Uvicorn + Pydantic v2**：提供 `/api/health`、`/api/funds/latest`（依個股聚合抽抽樂池）與 `/api/funds/by_etf`（依 ETF 分組權重明細）三個唯讀 JSON API。
  - **跨投信名稱正規化與代號映射**：聚合器自動清除狀態標記（如尾端 `*`）、套用精確跨投信別名映射（如將 `009816` 之 `創意電子` 與 `00403A` / `00981A` / `symbol.json` 之 `創意` 合併為 `3443 創意`），並結合 `symbol.json` 補齊股票代號與產業分類。
  - **合成示範資料產生器（`backend/scripts/seed_demo_data.py`）**：純 Python 標準庫實作，無須啟動爬蟲即可產生符合 `StockPriceSnapshot` 嚴格 Schema 的合成資料。
- **前端（Frontend）**：
  - **Vue 3 (Composition API) + TypeScript + Pinia + Vue Router + Vite 8**：零外部 UI 框架，採用原生 CSS 與響應式版型。
  - **Web Audio API 即時合成音效**：抽籤滾動（`play_tick`）、結果揭曉（`play_ding`）與拉霸音效全數由瀏覽器原生振盪器即時合成，不依賴外部音訊檔案；另支援透過選用 `VITE_BGM_URL` 載入自訂背景音樂。
  - **建置期安全白名單與 Puppeteer 靜態預渲染**：`vite.config.ts` 停用全量 `public/` 複製，僅透過 Rollup `generateBundle` 輸出 `favicon.svg`、`robots.txt` 與 `sitemap.xml`，並由 `frontend/scripts/prerender.mjs` 於建置期預渲染全部 6 條路由。

---

## 專案目錄結構

```text
DestinyOrder/
├── backend/
│   ├── core/
│   │   ├── funds/              # ETF 快照聚合器 (lucky_aggregator, etf_aggregator)、爬蟲註冊表、排程與 twse_securities.py
│   │   └── shared/             # 集中路徑/環境變數設定 (config.py) 與日誌處理
│   ├── routers/                # FastAPI 路由 (/api/funds/latest, /api/funds/by_etf)
│   ├── schemas/                # Pydantic v2 嚴格資料模型 (StockPriceSnapshot 等)
│   ├── scripts/
│   │   └── seed_demo_data.py   # 合成示範資料產生器 Canonical 實作（支援容器內 python -m 執行）
│   ├── tests/                  # 後端標準庫 unittest 測試套件（別名合併、合成資料原子提交、發布安全掃描自測）
│   ├── Dockerfile              # 後端容器建置檔
│   ├── main.py                 # FastAPI 應用程式入口
│   └── requirements.txt        # 後端 Python 鎖定依賴清單
├── frontend/
│   ├── e2e/
│   │   ├── local-recovery.spec.ts # Playwright 完整端對端驗證套件（API、抽選、拉霸、篩選、權重逐列核對）
│   │   └── vue.spec.ts         # 最小首頁載入煙霧測試
│   ├── public/
│   │   ├── favicon.svg         # 純幾何向量圖示（唯一白名單納入建置之靜態圖示）
│   │   ├── robots.txt          # 開發參考範本（建置時由 Vite plugin 依 VITE_SITE_URL 動態生成）
│   │   └── sitemap.xml         # 開發參考範本（建置時由 Vite plugin 依 VITE_SITE_URL 動態生成）
│   ├── scripts/
│   │   └── prerender.mjs       # Puppeteer 六路由靜態預渲染腳本
│   ├── src/
│   │   ├── __tests__/          # Vitest 單元與整合測試 (App.spec.ts)
│   │   ├── components/         # 全域導覽選單、音效按鈕、頁尾與免責聲明對話框
│   │   ├── composables/        # 幾何骰子動態 Favicon 等共用組合式函式
│   │   ├── router/             # Vue Router 路由定義、SEO Head 更新與嚴格 VITE_SITE_URL 驗證
│   │   ├── stores/             # Pinia 狀態管理 (funds API 快取、Web Audio 音效合成)
│   │   ├── types/              # 前端 TypeScript 型別定義
│   │   └── views/              # 六大頁面元件 (LuckyDraw, SlotMachine, HoldingsView, WeightsView, AboutView, FaqView)
│   ├── .env.example            # 前端 Vite 專用環境變數範本（可複製為 frontend/.env.local）
│   ├── Dockerfile              # 前端兩階段容器建置檔 (node:24-bookworm-slim -> nginx:alpine)
│   ├── package.json            # 前端腳本與依賴定義
│   ├── playwright.config.ts    # Playwright 預設設定（對齊 playwright.recovery.config.ts）
│   └── vite.config.ts          # Vite 建置、安全靜態白名單與 /api 反向代理設定
├── scripts/
│   ├── audit_publication.py    # 開源發布前本機安全、隱私與資產權利盤點掃描器
│   └── seed_demo_data.py       # 根目錄 CLI 薄轉發層（委派至 backend.scripts.seed_demo_data）
├── docs/
│   └── deployment.md           # 環境變數邊界、本機代理與 Docker Compose Profile 部署指南
├── .env.example                # Docker Compose 與本機環境變數參考範本
├── .gitignore                  # Git 忽略規則（排除機密、真實爬蟲資料、未知權利資產與封存備份檔）
├── docker-compose.yml          # 容器編排定義（預設僅啟 Web+API；crawler 與 tunnel 納入選用 profiles）
├── LICENSE                     # 專案開源授權條款（MIT License，適用於本版本庫公開之自有原創內容）
└── THIRD_PARTY_NOTICES.md      # 專案授權邊界、第三方圖示/套件授權聲明與金融資料來源限制
```

---

## 五檔 ETF 資料來源與更新機制

本專案設計支援以下五檔台股 ETF 與 TWSE 證券清單（**注意：所有爬蟲預設皆不自動啟動，公開版本庫亦不含任何真實抓取資料**）：

| 代號 | 名稱 | 類型 | 發行商資料來源模組 |
| :--- | :--- | :--- | :--- |
| `0050` | 元大台灣卓越 50 基金 | 被動市值型 | `backend/core/funds/crawlers/yuanta_0050.py` |
| `006208` | 富邦台灣采吉 50 基金 | 被動市值型 | `backend/core/funds/crawlers/fubon_006208.py` |
| `009816` | 凱基台灣 TOP 50 ETF 基金 | 被動市值型 | `backend/core/funds/crawlers/kgi_009816.py` |
| `00403A` | 主動統一台股升級 50 ETF 基金 | 主動式股票 ETF | `backend/core/funds/crawlers/uni_00403a.py` |
| `00981A` | 主動統一台股增長 ETF 基金 | 主動式股票 ETF | `backend/core/funds/crawlers/uni_00981a.py` |

- **資料儲存結構**：基金快照依日期存放於 `FUNDS_DATA_ROOT/yyyy/mm/dd/<code>.json`，證券代號與產業對照表存放於 `FUNDS_DATA_ROOT/symbol.json`（及 `symbol.csv`），TWSE 上市/上櫃 ISIN 清單解析模組位於 `backend/core/funds/twse_securities.py`。
- **聚合讀取機制**：後端 API 每次收到請求時，由 `find_latest_dated_dir()` 自動依年、月、日字典序倒排搜尋最新一個含有有效快照的日期資料夾，並與同一資料根目錄下的 `symbol.json` 進行正規化比對。
- **選用後端爬蟲說明（預設停用）**：後端爬蟲與排程器預設**絕不自動啟動**。若開發者自行確認符合各官方網站服務條款後欲手動執行爬蟲，除安裝 `backend/requirements.txt` 外，尚需於後端虛擬環境執行 `.\venv\Scripts\python.exe -m playwright install chromium` 安裝 Python Playwright Chromium 核心。

---

## 系統需求與實測版本

- **作業系統**：**Windows 11**（本輪本機開發完整實測；Windows 10 預期可用但本輪未實測）與 **Linux**（支援容器化環境，`seed_demo_data.py` 之 `renameat2(RENAME_NOREPLACE)` 已做隔離測試，惟**本輪尚未執行完整 Docker 映像建置與容器群啟動驗收**，且**尚未於全新空白機器驗證 Fresh Install**）；其他作業系統（如 macOS）未經實測，且 `seed_demo_data.py` 於未支援目錄級 `RENAME_NOREPLACE` 之系統會安全中止（fail closed）
- **Python 與 pip**：`Python >= 3.11` 且含標準 `venv` / `pip`（本機實測環境為 **Python `3.12.3`**；後端容器映像為 `python:3.11-slim`）
- **Node.js 與 npm**：`Node.js ^22.12.0 || >=24.0.0`（因 `puppeteer@25.0.4` 要求 `>= 22.12.0`，已排除 Node 20；本機實測環境與推薦版本為 **Node.js `24.12.0`**，前端容器建置階段為 `node:24-bookworm-slim`）

---

## 快速開始（Windows PowerShell 本機開發）

### 0. 取得原始碼並進入專案根目錄

```powershell
git clone https://github.com/LaimoKarca/DestinyOrder.git
cd DestinyOrder
```

> 以下各步驟皆標註對應之**工作目錄**，請留意終端機所在路徑。

### 1. 建立後端虛擬環境並安裝依賴（工作目錄：專案根目錄 `DestinyOrder/`）

確認 `python --version` 為 `3.11` 以上後執行：

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 2. 安裝前端依賴（工作目錄：`DestinyOrder/frontend/`）

確認 `node --version` 符合 `^22.12.0 || >=24.0.0` 後執行：

```powershell
cd frontend
npm ci
cd ..
```

### 3. 產生合成示範資料（工作目錄：專案根目錄 `DestinyOrder/`）

公開版本庫**不包含**任何真實抓取之歷史快照資料（`backend/data/funds/`）。首次 clone 專案後，請於**專案根目錄**執行內建純標準庫腳本產生**合成示範資料**：

```powershell
.\venv\Scripts\python.exe scripts\seed_demo_data.py
```

（或以模組方式執行：`.\venv\Scripts\python.exe -m backend.scripts.seed_demo_data`）

- **示範資料辨識說明**：
  - 合成示範資料固定使用歷史示範日期 **`2000/01/03`**。
  - 成分股皆為虛構公司與代號（`DEMO1 示範半導體`、`DEMO2 示範金控`、`DEMO3 示範電信`、`DEMO4 示範航運`、`DEMO5 示範生技`、`DEMO6 示範精密`），ETF 名稱亦明確標註 `（合成示範資料）`，絕不代表真實市場行情。
- **安全保護機制**：
  - `seed_demo_data.py` 採用「同父目錄暫存 + 單次原子目錄 `rename`」機制，嚴格要求目標路徑（預設 `backend/data/funds`）**尚不存在**；若目標路徑已存在（含任何非空目錄、空目錄或檔案），腳本會立即拒絕並以非 0 狀態結束，絕不刪除或覆寫任何既有檔案。
  - 若本機已有真實資料但想額外測試合成示範資料，可搭配 `--target-dir` 與 `DESTINYORDER_FUNDS_DATA_ROOT` 環境變數指定一個**尚不存在**的新目標路徑：

```powershell
.\venv\Scripts\python.exe scripts\seed_demo_data.py --target-dir .\tmp_demo_funds
$env:DESTINYORDER_FUNDS_DATA_ROOT = (Resolve-Path .\tmp_demo_funds).Path
```

### 4. 啟動後端與前端開發服務

開兩個 PowerShell 終端機視窗分別啟動：

**終端機 1 — 後端 API（工作目錄：專案根目錄 `DestinyOrder/`，預設 `http://127.0.0.1:8000`）**：

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**終端機 2 — 前端 Vite Dev Server（工作目錄：`DestinyOrder/frontend/`，預設 `http://127.0.0.1:5173`）**：

```powershell
cd frontend
npx vite --host 127.0.0.1 --port 5173 --strictPort
```

瀏覽器開啟 <http://127.0.0.1:5173> 即可操作完整六個頁面。

---

## 測試、型別檢查與建置驗證

### 1. 後端單元與安全回歸測試（工作目錄：專案根目錄 `DestinyOrder/`）

```powershell
.\venv\Scripts\python.exe -B -m unittest discover -s backend/tests -v
```

### 2. 前端型別檢查、唯讀 Lint 與單元測試（工作目錄：`DestinyOrder/frontend/`）

若當前位於專案根目錄，請先執行 `cd frontend` 進入前端目錄（若已在 `frontend/` 內則無須重複切換）：

```powershell
npm run type-check
npm run lint
npm run test:unit -- --run
```

### 3. 前端端對端測試（Playwright E2E，工作目錄：`DestinyOrder/frontend/`）

> **瀏覽器核心區分說明**：前端 E2E 測試使用 **`@playwright/test`（Playwright Chromium）**，而第 4 節預渲染建置使用 **`puppeteer`（Puppeteer Chrome）**，兩者管理各自獨立的瀏覽器快取。

首次於新環境執行 Playwright E2E 前，請在 `frontend/` 目錄下安裝 Playwright 專用之 Chromium：

```powershell
npx --no-install playwright install chromium
```

確認後端（`127.0.0.1:8000`）與前端（`127.0.0.1:5173`）已啟動後，於 `frontend/` 目錄執行：

```powershell
npm run test:e2e
```

（若欲針對隔離連接埠如 `http://127.0.0.1:5174` 執行驗證，可設定 `$env:E2E_BASE_URL="http://127.0.0.1:5174"; npm run test:e2e`。）

### 4. 前端正式建置與預渲染（Build & Prerender，工作目錄：`DestinyOrder/frontend/`）

於 `frontend/` 目錄執行完整建置（含 `vue-tsc` 型別檢查、Vite 打包與 Puppeteer 六路由預渲染）：

```powershell
npm run build
```

- **Puppeteer 預渲染瀏覽器說明**：
  - `npm ci` 安裝 `puppeteer` 時預設會自動下載對應之 Chrome for Testing 二進位檔供 `frontend/scripts/prerender.mjs` 使用。
  - 若於網路受限環境、快取未命中或曾設定 `PUPPETEER_SKIP_DOWNLOAD` 導致預渲染階段找不到 Chrome，可於 `frontend/` 執行：
    ```powershell
    npx --no-install puppeteer browsers install chrome
    ```
    或設定環境變數 `$env:PUPPETEER_EXECUTABLE_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"` 指向系統既有 Chrome/Chromium。
  - 若僅需產生前端靜態 bundle 而無需執行預渲染，可改執行：
    ```powershell
    npm run build:no-prerender
    ```

---

## 已知限制（Known Limitations）

1. **公開範圍不含真實金融資料集**：TWSE 網站條款限制未經許可之自動化下載與再散布，元大投信官網具明確著作權保留聲明，且本輪針對各投信來源網站均**未能確認適用於抓取後成分股快照之公開再散布授權**（並非概括宣稱每家投信皆已證實禁止）。為嚴守合規邊界，公開儲存庫僅提供 `2000/01/03` 合成示範資料產生器（詳見 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)）。
2. **本機歷史 `symbol.json` / `symbol.csv` 字面 `U+FFFD` 紀錄**：本機既有 `backend/data/funds/symbol.json` 與 `symbol.csv`（已排除於 Git 之外）雖可嚴格通過 `utf-8-sig` 解碼且現有五檔 ETF API 達 0 筆 `null` symbol，但檔案內容帶有 486 個原已存在之字面 `U+FFFD` 替換字元（可能源於上游網頁或早期歷史轉碼，根因未驗證）。
3. **`backend/requirements.txt` 編碼**：目前 `backend/requirements.txt` 為 UTF-16LE（含 BOM）編碼（共 24 個套件鎖定），Windows 本機 `pip` 可正常讀取，若於其他自訂文字處理工具讀取請留意編碼。
4. **全新空白機器安裝（Fresh Install）與完整 Docker 建置/啟動尚未實測**：本輪復原與開源準備係於既有開發機環境完成本機驗證，**尚未在全新空白機器上實際驗證從零 Fresh Install**；Docker 部分僅驗證安全語法檢查（`docker compose --env-file .env.example config --quiet`）與 Linux 隔離環境下之 `seed_demo_data.py` 測試，**尚未執行完整 `docker compose build` 映像重建與 `docker compose up` 容器群啟動驗收**（詳見 [`docs/deployment.md`](./docs/deployment.md)）。
5. **專案授權邊界與已排除之本機資產**：本次公開版本庫所含之自有原創程式碼、文案、幾何 SVG 圖示與 Web Audio 即時音效合成邏輯已由專案擁有者（`LaimoKarca`）正式採用 [`LICENSE`](./LICENSE)（**MIT License**）授權，第三方元件與相依套件則保留其各自原始授權條款；非必要之本機離線腳本（`scripts/generate_favicon.py`、`scripts/render_lottery_sfx.py`）、點陣圖示、`og-image.png`、未確認權利之音訊檔與真實抓取之 ETF 資料集則**不包含於本次公開與 MIT 授權範圍內**，維持透過 `.gitignore` 排除（詳見 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)）。
6. **發布前安全掃描器之範圍限制與可選私有網域設定**：`scripts/audit_publication.py` 採用啟發式正則規則對常見機密、內嵌帳密 URL、結構化 Token 與個人識別資訊進行靜態掃描（預設不含任何私人 hostname，僅偵測通用公開穿隧尾綴如 `trycloudflare.com`；若維護者欲於本機額外檢查特定私有/舊部署網域，可於執行掃描前設定可選環境變數 `DESTINYORDER_AUDIT_PRIVATE_HOSTS="host1.example,host2.example"`，報告一律以 `[HOST_REDACTED]` 遮蔽輸出）。其單元自測涵蓋有限之合成測試樣本，不等同於可保證檢出所有未知格式憑證之形式化證明，公開前仍須結合 `.gitignore` 與人工審閱候選檔案清單。
