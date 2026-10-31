# DestinyOrder Frontend

本目錄為 **DestinyOrder — 台股 ETF 命定抽抽樂** 的前端應用程式（Vue 3 + TypeScript + Pinia + Vue Router + Vite 8）。

- **完整專案說明、後端與合成示範資料初始化**：請先參閱根目錄 [`../README.md`](../README.md)
- **環境變數邊界、靜態白名單預渲染與容器部署指南**：請參閱 [`../docs/deployment.md`](../docs/deployment.md)

---

## 環境需求

- **Node.js**：`^22.12.0 || >=24.0.0`（推薦 **`24.12.0`**；因 `puppeteer@25.0.4` 要求 `>= 22.12.0`，不支援 Node 20）
- **後端服務**：開發與 E2E 測試時需先於專案根目錄完成 `python scripts/seed_demo_data.py` 初始化並啟動 FastAPI 後端（預設 `http://127.0.0.1:8000`），Vite 會自動將 `/api` 代理轉發至後端。

---

## 常用指令（工作目錄：`DestinyOrder/frontend/`）

```powershell
# 1. 安裝鎖定依賴
npm ci

# 2. 啟動開發伺服器（預設 http://127.0.0.1:5173）
npx vite --host 127.0.0.1 --port 5173 --strictPort

# 3. TypeScript 型別檢查與唯讀 Lint（不自動修改檔案）
npm run type-check
npm run lint

# 4. 單次執行 Vitest 單元與整合測試
npm run test:unit -- --run

# 5. 正式建置與 Puppeteer 六路由靜態預渲染
#    （若環境受限未自動下載 Puppeteer Chrome，可先執行 npx --no-install puppeteer browsers install chrome，
#      或設定 PUPPETEER_EXECUTABLE_PATH；僅需打包不預渲染可執行 npm run build:no-prerender）
npm run build

# 6. Playwright 端對端測試（首次執行需先安裝 Playwright Chromium，且需先啟動後端 8000 與前端 5173）
npx --no-install playwright install chromium
npm run test:e2e
```

---

## 前端環境變數

前端僅讀取程序環境變數或本目錄下的 `frontend/.env.local`（可由 [`.env.example`](./.env.example) 複製），**不會讀取專案根目錄的 `.env`**。切勿將含有私密憑證（如 `CLOUDFLARED_TOKEN`）的根目錄 `.env` 複製進 `frontend/`。
