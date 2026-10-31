# DestinyOrder 部署與環境設定指南

本文件說明 DestinyOrder 的環境變數讀取邊界、本機反向代理配置、靜態預渲染建置流程，以及 Docker Compose 容器化初始化與選用 Profiles（`crawler` 與 `tunnel`）。

> **重要驗證範圍與機密安全警告**：
> - **完整 Docker 建置與啟動尚未實測**：本輪開源準備僅針對 [`docker-compose.yml`](../docker-compose.yml) 執行安全語法檢核（`docker compose --env-file .env.example config --quiet`）與 Linux 隔離環境下之 `seed_demo_data.py` 原子提交測試，**尚未執行完整 `docker compose build` 映像重建與 `docker compose up` 多容器啟動驗收**；全新空白機器之 Fresh Install 亦尚未實測。
> - **嚴禁直接執行或張貼展開後之 `docker compose config`**：當專案根目錄存在含有真實憑證的 `.env` 時，執行未帶 `--env-file .env.example` 與 `--quiet` 的 `docker compose config` 會將機密 Token 明文插值展開並輸出至終端機。**切勿在終端機直接印出、截圖或於 Issue / 工單 / 日誌中張貼展開後的 Compose 組態輸出**；開發與語法驗證請一律加上 `--env-file .env.example`。

---

## 1. 環境變數讀取邊界（重要）

本專案不同執行元件讀取環境變數的位置各自獨立，**請勿混淆根目錄 `.env` 與本機前端/後端設定**：

1. **專案根目錄 `.env`（由 [`.env.example`](../.env.example) 複製）**：
   - **僅供 Docker Compose 使用**：用於 [`docker-compose.yml`](../docker-compose.yml) 的變數插值（如 `VITE_SITE_URL` build arg 與 `tunnel` profile 的 `CLOUDFLARED_TOKEN`）。若僅進行一般開發或不含 Tunnel 的容器操作，建議直接使用 `--env-file .env.example` 以避免誤讀根目錄 `.env`。
   - **本機裸機執行不會自動讀取根目錄 `.env`**：後端 Python 並未載入 `python-dotenv`，前端 Vite 的 `envDir` 則固定為 `frontend/` 目錄。
2. **本機後端（Python / Uvicorn）**：
   - 直接由作業系統程序環境變數（`os.environ`）讀取。
   - 在 Windows PowerShell 中，可於啟動後端前透過 `$env:變數名="值"` 設定資料路徑或跨域清單（例如 `$env:DESTINYORDER_FUNDS_DATA_ROOT="C:\path\to\demo_funds"`、`$env:DESTINYORDER_CORS_ORIGINS="http://127.0.0.1:5173"`）。
   - **注意 Uvicorn CLI 與 `main.py` 啟動方式之差異**：若以推薦指令 `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` 啟動，綁定主機與連接埠由 CLI 參數 `--host` 與 `--port` 決定；環境變數 `DESTINYORDER_HOST` 與 `DESTINYORDER_PORT` **僅在直接執行 `python backend/main.py`（進入 `__main__` 區塊）時生效**。
3. **本機前端（Vite Dev / Preview / Build）**：
   - 由程序環境變數（`$env:VITE_SITE_URL` 等）或 **`frontend/.env.local`**（可由 [`frontend/.env.example`](../frontend/.env.example) 複製）讀取。
   - **安全鐵律**：**嚴禁將含有 `CLOUDFLARED_TOKEN` 或任何私密憑證的根目錄 `.env` 複製或移動至 `frontend/` 目錄下**。任何以 `VITE_` 開頭的變數都會被打包進公開的前端 JavaScript bundle 中。

### 環境變數一覽表

| 變數名稱 | 實際讀取元件與方式 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `DESTINYORDER_HOST` | 後端 `os.environ` (`backend/main.py` `__main__`) | `127.0.0.1` | **僅直接執行 `python backend/main.py` 時生效**；若使用 `uvicorn` CLI 請改傳 `--host` |
| `DESTINYORDER_PORT` | 後端 `os.environ` (`backend/main.py` `__main__`) | `8000` | **僅直接執行 `python backend/main.py` 時生效**；若使用 `uvicorn` CLI 請改傳 `--port` |
| `DESTINYORDER_CORS_ORIGINS` | 後端 `os.environ` (`backend/main.py`) | `http://localhost:5173,http://127.0.0.1:5173` | 允許跨域請求的前端 Origin 清單（逗號分隔） |
| `DESTINYORDER_DATA_ROOT` | 後端 `os.environ` (`backend/core/shared/config.py`) | `backend/data` | 後端資料根目錄（空字串/純空白自動回退預設；相對路徑固定相對於專案根目錄 `PROJECT_ROOT`） |
| `DESTINYORDER_FUNDS_DATA_ROOT` | 後端 `os.environ` (`config.py` / `seed_demo_data.py`) | `backend/data/funds` | ETF 快照與 `symbol.json` 所在目錄（空字串/純空白自動回退預設；相對路徑固定相對於 `PROJECT_ROOT`） |
| `VITE_SITE_URL` | 前端程序環境變數 / `frontend/.env.local` / Docker build arg | `http://127.0.0.1:5173` | 網站對外基準 Origin（必須為 `http://` 或 `https://` 且無帳密、路徑、query 或 hash），用於 canonical、OG、JSON-LD、`robots.txt` 與 `sitemap.xml` |
| `VITE_BGM_URL` | 前端程序環境變數 / `frontend/.env.local` (`src/App.vue`) | `""`（空字串） | 選用背景音樂 URL；預設留空不載入任何外部音訊檔 |
| `BACKEND_API_TARGET` | Vite Server 程序環境變數 / `frontend/.env.local` (`vite.config.ts`) | `http://127.0.0.1:8000` | **僅 Vite 伺服器端讀取**（不含 `VITE_` 前綴，不進入前端 bundle），設定 `/api` 代理轉發目標 |
| `CLOUDFLARED_TOKEN` | 根目錄 `.env` 供 Docker Compose (`tunnel` profile) 插值 | `""`（空字串） | **機密變數**：僅在啟用 `--profile tunnel` 時傳遞給 `cloudflared` 容器，嚴禁放入 `frontend/` 或 `VITE_*` |

---

## 2. 靜態資產白名單與預渲染建置（Build & Prerender）

於 `frontend/` 目錄執行 `npm run build` 時會依序執行：

1. **`npm run type-check` (`vue-tsc --build`)**：驗證全專案與測試檔 TypeScript 型別。
2. **`npm run build-only` (`vite build`)**：
   - `vite.config.ts` 設定 `publicDir: false` 並啟用 `siteMetadataAndSafePublicPlugin`。
   - 先以 `new URL()` 嚴格驗證 `VITE_SITE_URL` 為合法 `http/https` origin（若非法則拋出固定錯誤訊息，絕不回顯輸入字串以防止注入），並將 `index.html` 內的 `__SITE_URL__` 替換為該 origin，同時透過 `define` 注入 `import.meta.env.VITE_SITE_URL`。
   - 於 Rollup `generateBundle` 階段透過 `this.emitFile` 輸出 `favicon.svg`、`robots.txt` 與 `sitemap.xml`（遵循 resolved `outDir`，且不會在 Vitest 或 dev server 關閉時寫檔）。
3. **`npm run prerender` (`node scripts/prerender.mjs`)**：
   - 啟動本機暫存靜態伺服器並透過 Puppeteer（Chrome for Testing）依序造訪 `/`、`/slot`、`/holdings`、`/weights`、`/about`、`/faq` 六條路由，將掛載後的 HTML 寫入 `dist/<route>/index.html`。
   - 若環境受限未自動下載 Puppeteer Chrome，可執行 `npx --no-install puppeteer browsers install chrome` 或指定 `PUPPETEER_EXECUTABLE_PATH`；若僅需建置 SPA bundle 而無需執行預渲染，可執行 `npm run build:no-prerender`。

---

## 3. Docker Compose 容器化部署與合成資料初始化

> **注意**：如文首所述，本輪僅驗證 `docker compose --env-file .env.example config --quiet` 組態語法與 Linux 隔離環境下之 `seed_demo_data.py` 測試，**尚未實測完整 `docker compose build` 與 `docker compose up` 容器群啟動流程**。

[`docker-compose.yml`](../docker-compose.yml) 將服務拆分為預設核心服務（`backend-api` + `frontend`）與兩個選用 Profile（`crawler` 與 `tunnel`）。

### 3.1 預設開發/示範模式：語法檢查、建置、首次合成資料初始化與啟動

後端 Dockerfile（`backend/Dockerfile`）僅建立 `/app/backend/data` 父目錄而不預先建立 `funds` 子目錄，且已將合成示範資料產生器 Canonical 實作納入 `/app/backend/scripts/seed_demo_data.py`。為避免誤讀取本機根目錄 `.env` 中可能存在的私密憑證，開發與示範模式建議顯式指定 `--env-file .env.example`：

```bash
# 1) 安全驗證 Compose 設定語法（指定 .env.example 並加上 --quiet，避免將任何環境變數明文展開印出至終端機）
docker compose --env-file .env.example config --quiet

# 2) 建置後端與前端容器映像
docker compose --env-file .env.example build

# 3) 於空白的 funds_data volume 單次執行合成示範資料初始化
#    注意：若 volume 內的 /app/backend/data/funds 已存在（含既有資料），此命令會安全拒絕覆寫並返回非 0
docker compose --env-file .env.example run --rm --no-deps backend-api python -m backend.scripts.seed_demo_data

# 4) 啟動核心 Web (port 80) + API 服務
docker compose --env-file .env.example up -d
```

### 3.2 選用 Profile 1：背景爬蟲（`--profile crawler`）

> **注意**：啟用爬蟲前，請先閱讀 [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)，確認您的使用方式符合臺灣證券交易所（TWSE）與各 ETF 發行商之網站使用條款及頻率限制。

```bash
docker compose --env-file .env.example --profile crawler up -d
```

此 Profile 會額外啟動：
- `backend-scheduler`（`python -m backend.run_scheduler`）
- `backend-twse`（`python -m backend.run_twse_securities`）

### 3.3 選用 Profile 2：Cloudflare Tunnel（`--profile tunnel`）

若需透過 Cloudflare Tunnel 對外發布服務，請先於專案根目錄 `.env`（勿提交至 Git）設定有效的 `CLOUDFLARED_TOKEN` 與 `VITE_SITE_URL`，再顯式啟用 `tunnel` profile（**再次提醒：切勿對含有真實 `.env` 的環境執行未加 `--quiet` 的 `docker compose config`，亦切勿將展開後的設定貼至終端機紀錄或工單**）：

```bash
docker compose --profile tunnel up -d
```
