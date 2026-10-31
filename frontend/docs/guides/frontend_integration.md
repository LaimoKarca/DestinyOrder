# 前端整合說明

> **現行安裝、測試與部署主指南請以專案根目錄 [`README.md`](../../../README.md) 與 [`docs/deployment.md`](../../../docs/deployment.md) 為準。**
> 後端對應文件：[backend/docs/api_docs.md](../../../backend/docs/api_docs.md)。
> 頁面架構見 [architecture/frontend_sitemap.md](../architecture/frontend_sitemap.md)。
> 抽抽樂 API 互動循序圖見 [backend lucky_draw_sequence.md](../../../backend/docs/architecture/lucky_draw_sequence.md)。

---

## 技術棧

| 項目 | 版本 / 設定 |
|------|------------|
| 框架 | Vue 3 `^3.5.32`（`<script setup lang="ts">`） |
| 路由 | vue-router `^5.0.4`，`createWebHistory`（共 6 條路由：`/`、`/slot`、`/holdings`、`/weights`、`/about`、`/faq`） |
| 狀態管理 | Pinia `^3.0.4`（用於 `stores/funds.ts` 資料快取與 `stores/audio.ts` 音效狀態管理） |
| Build / Dev | Vite `^8.0.8` + Puppeteer 預渲染腳本（`scripts/prerender.mjs`） |
| Lint / Format | ESLint flat config + oxlint（預設唯讀檢查） + Prettier |
| Test | Vitest + Vue Test Utils（`src/__tests__/App.spec.ts`）、Playwright（`e2e/local-recovery.spec.ts`、`e2e/vue.spec.ts`） |

---

## 目錄結構

```
frontend/
├── index.html                       ← 入口 HTML（title 已客製為「DestinyOrder · 台股 ETF 抽抽樂」）
├── vite.config.ts                   ← Vite 設定；含靜態資產安全白名單與 /api proxy 至後端
├── scripts/
│   └── prerender.mjs                ← Puppeteer 六路由靜態預渲染腳本
├── src/
│   ├── main.ts                      ← createApp + Pinia + Router
│   ├── App.vue                      ← 全域 <AppMenu /> + <SpeakerButton /> + <RouterView /> + <AppFooter />
│   ├── router/index.ts              ← 路由表（/、/slot、/holdings、/weights、/about、/faq）
│   ├── views/
│   │   ├── LuckyDraw.vue            ← / 主頁面（抽抽樂）
│   │   ├── SlotMachine.vue          ← /slot（命定拉霸機，懶載入）
│   │   ├── HoldingsView.vue         ← /holdings（五檔 ETF 成分股一覽，懶載入）
│   │   ├── WeightsView.vue          ← /weights（各 ETF 權重查詢，懶載入）
│   │   ├── AboutView.vue            ← /about（關於本站，懶載入）
│   │   └── FaqView.vue              ← /faq（常見問題，懶載入）
│   ├── components/
│   │   ├── AppMenu.vue              ← 左上角漢堡導覽選單（含六大路由連結）
│   │   ├── SpeakerButton.vue        ← 右上角音效開關按鈕
│   │   └── AppFooter.vue            ← 全域頁尾與免責聲明對話框
│   ├── stores/
│   │   ├── funds.ts                 ← Pinia store — 跨頁面共享的 funds 資料快取
│   │   └── audio.ts                 ← Pinia store — Web Audio 合成音效與靜音狀態
│   ├── services/funds.ts            ← API client（fetch_latest_funds / fetch_funds_by_etf + 隨機抽）
│   └── types/funds.ts               ← 與後端 schema 對齊的 TS 介面
└── docs/                            ← 本文件所在
```

> Vue DevTools 插件 (`vite-plugin-vue-devtools`) 已從 `vite.config.ts` 移除；瀏覽器仍可透過 Vue.js Devtools 擴充功能除錯，但不再出現頁面內的浮動工具列。

---

## API 整合

### 端點

| 端點 | 來源 | 對應前端模組 |
|------|------|------------|
| `GET /api/funds/latest` | [backend/routers/funds.py](../../../backend/routers/funds.py) | [services/funds.ts](../../src/services/funds.ts) `fetch_latest_funds()` |
| `GET /api/funds/by_etf` | [backend/routers/funds.py](../../../backend/routers/funds.py) | [services/funds.ts](../../src/services/funds.ts) `fetch_funds_by_etf()` |

### Dev Proxy

[vite.config.ts](../../vite.config.ts) 設定：

```ts
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: false,
    },
  },
}
```

前端只認得 `/api/*`，由 Vite 在 dev mode 轉發到 FastAPI。**正式部署** 需另由反向代理（Nginx 等）做同樣轉發，否則需依賴後端 `CORSMiddleware`。

### 型別對齊

[src/types/funds.ts](../../src/types/funds.ts) 與後端 [schemas/funds_lucky.py](../../../backend/schemas/funds_lucky.py) 採 **同名 snake_case 欄位**（`etf_code`、`etf_name`），FastAPI 預設不轉 camelCase，前端直接照收。

| 後端 Schema | 前端 Interface | 必對齊欄位 |
|------------|---------------|----------|
| `DrawSource` | `DrawSource` | `etf_code`, `etf_name`, `weight` |
| `DrawableStock` | `DrawableStock` | `name`, `symbol`, `industry`, `sources` |
| `FundsLuckyResponse` | `FundsLuckyResponse` | `date`, `etf_codes`, `stocks` |

> 若任一端要改名，**兩邊同時改**，並更新 [backend api_docs.md](../../../backend/docs/api_docs.md)。

### 錯誤處理

`fetch_latest_funds()` 對非 2xx 嘗試解析 `{ detail }`：

| 後端回應 | 前端行為 |
|---------|---------|
| `2xx` + JSON | 正常 return |
| `4xx`/`5xx` + `{ detail }` | `throw new Error("<detail>（HTTP <status>）")` |
| `4xx`/`5xx` + 非 JSON | `throw new Error("載入基金資料失敗 (HTTP <status>)")` |

LuckyDraw 在 `onMounted` 內捕捉並寫入 `error.value`，UI 切換成錯誤狀態並提示「請確認後端資料夾 backend/data/funds 存在且包含最新日期」。

---

## LuckyDraw 頁面行為

### 狀態機

| 狀態 | 觸發 | UI |
|------|------|-----|
| `loading` | 初始進入 onMounted | spinner + 「載入最新基金成分股…」 |
| `error` | `fetch_latest_funds()` reject | 紅字錯誤 + 排查提示 |
| `idle` | 成功取得 pool，尚未抽 | 卡片顯示「等待開獎」pill，按鈕文案為「開始抽抽」 |
| `rolling`（1.4s） | 點擊 `draw()` | 多層光環瘋狂反向自轉 / 卡片呼吸縮放 + 抖動 / aurora 暴閃 / 名稱抖動模糊 |
| `revealing`（0.78s） | rolling 結束的「釘下去」瞬間 | 全螢幕白光閃 + 螢幕震動 + 衝擊波雙環擴散 + 名稱印章動畫 + WebAudio PONG 音效 + `navigator.vibrate` |
| `revealed` | revealing 結束 | 顯示命運標的（名稱 / 代號 / 產業別）與來源 ETF pills；按鈕文案改為「再抽一次」 |

> 三個過渡狀態（`rolling` / `revealing`）都會 `:disabled` 按鈕，避免在動畫中重複觸發。

### 抽取動畫

[LuckyDraw.vue](../../src/views/LuckyDraw.vue) `draw()`：

| 參數 | 預設 | 用途 |
|------|------|------|
| `totalMs` | `1400` | 總滾動時間 |
| `startInterval` | `38 ms` | 起始的「抖動」更新頻率 |
| `endInterval` | `170 ms` | 結束前的更新頻率（漸慢，符合 slot-machine 減速感） |

採 quadratic ease-out（`progress * progress`）線性插值，每個 tick 呼叫 `pick_random_stock()` 更新預覽。最後一次抽取結果寫入 `result.value`，然後 `revealing` 進入 780ms「釘下去」階段。

### 「PONG」音效合成

`play_pong()` 用 Web Audio API 合成 kick-drum 風格的低音：

| 層 | 設定 |
|----|------|
| Bass body | sine 180Hz → 38Hz `exponentialRampToValueAtTime`，0.55s 衰減，peak gain 0.9 |
| Click transient | 40ms 隨機 noise buffer，每 sample 乘 `exp(-i / (sr * 0.008))` 形成尖端衝擊 |
| Boom tail | 第二支 sine 60Hz → 28Hz，peak gain 0.35，0.7s 鬆鬆的低頻殘響 |

`AudioContext` 採 lazy 建立、首次 `draw()` 點擊時才實例化，避開 autoplay policy。`prefers-reduced-motion: reduce` 時直接 skip。

### 觸覺回饋

`buzz()` 呼叫 `navigator.vibrate?.([55, 30, 25])`，在支援的行動瀏覽器產生「咚 — 短 — 短」三段震動，與 PONG 音效對齊。`prefers-reduced-motion` 時 skip。

---

## 導覽與路由

左上角漢堡按鈕（[components/AppMenu.vue](../../src/components/AppMenu.vue)）為全域元件，在 [App.vue](../../src/App.vue) 與 `<RouterView />` 並列掛載。

| 路由 | 名稱 | View | 載入策略 |
|------|------|------|---------|
| `/` | `lucky-draw` | [views/LuckyDraw.vue](../../src/views/LuckyDraw.vue) | eager（首屏） |
| `/slot` | `slot-machine` | [views/SlotMachine.vue](../../src/views/SlotMachine.vue) | dynamic `import()` 懶載入 |
| `/holdings` | `holdings` | [views/HoldingsView.vue](../../src/views/HoldingsView.vue) | dynamic `import()` 懶載入 |
| `/weights` | `weights` | [views/WeightsView.vue](../../src/views/WeightsView.vue) | dynamic `import()` 懶載入 |
| `/about` | `about` | [views/AboutView.vue](../../src/views/AboutView.vue) | dynamic `import()` 懶載入 |
| `/faq` | `faq` | [views/FaqView.vue](../../src/views/FaqView.vue) | dynamic `import()` 懶載入 |

## SlotMachine 頁面行為

三軸（reel）並排，視窗顯示 3 列，**中列為中獎付線**。底層演算法先 `pick_random_stock()` 決定最終命中標的，再把它塞進每一軸滾動條的「倒數第二格」，使三軸停下後中列必然三連中。

| 狀態 | 觸發 | UI |
|------|------|-----|
| `idle` | 進頁 / 動畫結束 | 三軸顯示初始隨機格、按鈕「拉動拉桿」 |
| `rolling`（~2.9s） | 點擊 `pull_lever()` | 三軸用 CSS transition 滾動，分別 1.5s / 2.1s / 2.9s 落定；aurora 暴閃；持續 `play_tick()` |
| 每軸落定 | 經過該軸的 stop 時間點 | `play_ding()` + 中線金光高亮（`reel-pay-glow.active`） |
| `jackpot`（2.6s） | 第三軸落定後 | 螢幕震 + page-flash + 「命定！」飛字 + 42 片彩帶 + 16 顆金幣雨 + 3 連 ding |
| `revealed` | jackpot 結束 | 機台保留結果，產業 / ETF pills 顯示在 reels 下方；按鈕變「再拉一次」 |

關鍵常數位於檔頭：

| 常數 | 預設 | 用途 |
|------|------|------|
| `ITEM_HEIGHT` | `110` px | 單格高度；視窗總高 = 3 × ITEM_HEIGHT（mobile 走 80 / 72） |
| `REEL_DURATIONS` | `[1500, 2100, 2900]` ms | 三軸停止時間，差距製造「一個一個停」張力 |
| `STRIP_LENGTHS` | `[28, 38, 48]` | 三軸滾動條長度，後軸滾更久；最終格固定排在 `len - 2` |
| `VEGAS_OUTSET` | `12` px | 機台外環跑馬燈 SVG 的外擴距離 |

過場控制：先設 `duration=0` + `offset=0` 重置三軸並等 `requestAnimationFrame` × 2 確保「無 transition 的初始態」commit 進 DOM，再套上 `duration=REEL_DURATIONS[i]` 與終點 offset，觸發 CSS transition。

漢堡選單行為：

- 預設收合；點按鈕展開為小型下拉面板（非全寬 drawer）
- 六個 `<RouterLink>`：命定抽抽樂 / 命定拉霸機 / 五檔 ETF 成分股一覽 / 各 ETF 權重查詢 / 關於本站 / 常見問題
- 當前路由的項目高亮（依 `route.path` 比對）
- 觸發任一導覽後 `watch(() => route.path)` 自動收合
- ESC 鍵與背景點擊可關閉
- `aria-expanded` 與 `role="menu"` / `role="menuitem"` 補上鍵盤與螢幕報讀器語意

## Funds 資料快取（Pinia store）

各頁面共用 [stores/funds.ts](../../src/stores/funds.ts) 的 `use_funds_store()`，避免跨頁切換各自 fetch 重打 API。

| 方法 / 狀態 | 用途 |
|-------------|------|
| `ensure_loaded()` | 首次呼叫才打 API；後續呼叫 idempotent |
| `refresh()` | 強制重新抓（重設 `loaded=false`） |
| `stocks` / `etf_codes` / `data_date` | 對應 `FundsLuckyResponse` 三個欄位 |
| `loading` / `error` / `loaded` | 載入狀態旗標 |

`LuckyDraw.vue`、`SlotMachine.vue` 與 `HoldingsView.vue` 在 `onMounted` 皆呼叫 `ensure_loaded()`，誰先誰後都沒差。

### HoldingsView 篩選與排序

[views/HoldingsView.vue](../../src/views/HoldingsView.vue) 依 store 中的 `stocks` 做純前端篩選：

| 控制 | 行為 |
|------|------|
| 搜尋 input | 對 `symbol` 或 `name` 做不分大小寫的 `includes()` |
| 產業 `<select>` | 完全比對 `industry` |
| ETF chips | 多選，**OR 邏輯**（任一被選中的 ETF 持有此股就顯示） |
| 預設排序 | `sources.length` DESC（共同持有多者優先），同筆數再依 `name.localeCompare` |
| 「清除篩選」按鈕 | 只在任一條件有值時顯示 |

### HoldingsView 表格欄位

| 欄位 | 來源 | 備註 |
|------|------|------|
| 股票代號 | `stock.symbol` | 缺值顯示 `——`，tabular-nums |
| 名稱 | `stock.name` | — |
| 產業別 | `stock.industry` | 缺值顯示「未分類」 |
| **選股陣容** | `stock.sources[*].etf_code` | 標籤化呈現；`title` 顯示完整 ETF 名稱與權重 |

> 欄位名稱「選股陣容」用來描述「持有此股的 ETF 名單」，命名延續「命定抽選」主題；如需更改文案，**只動 [HoldingsView.vue](../../src/views/HoldingsView.vue) 的 `<th class="col-sources">`**。

### Pill 排序

`sortedSources` computed 依固定 `ETF_ORDER` (`0050, 006208, 009816, 00403A, 00981A`) 排序 source pills，避免每次重抽 pill 位置漂移。

> **新增 ETF 時**：把代號加入 [LuckyDraw.vue](../../src/views/LuckyDraw.vue) 的 `ETF_ORDER` 常數，同步更新此處表格與後端 [registry.py](../../../backend/core/funds/registry.py)。

### 資料日期顯示

`dataDate` 從後端 `FundsLuckyResponse.date` 帶入，渲染在頁尾免責聲明後，例：

> `※ 本工具僅供研究參考，不構成任何投資建議；實際投資決策請審慎評估。　資料日期：2026/05/24`

採純文字呈現（非 pill）；於 `max-width: 540px` 以下會自動斷行顯示。

### RWD 斷點

| 斷點 | 行為 |
|------|------|
| 預設（≥ 769px） | 桌機完整佈局 |
| `max-width: 768px` | 縮減 hero 與卡片間距 |
| `max-width: 540px` | 代號 / 產業別改直列；免責日期換行 |
| `max-width: 360px` | 主標題降階；按鈕擴展至 100% 寬 |
| `min-width: 1280px` | 卡片陰影更深、glow 更立體 |
| `prefers-reduced-motion: reduce` | 停掉所有滾動動畫與抖動 |

---

## 開發指令（完整流程請以根目錄 [`README.md`](../../../README.md) 為準）

```
npm ci                   # 安裝鎖定依賴
npm run dev              # Vite dev server (5173)；需後端 8000 已啟動
npm run type-check       # vue-tsc 型別檢查
npm run lint             # oxlint + eslint（預設唯讀檢查，不自動修改檔案）
npm run format           # prettier
npm run build            # type-check + vite build + Puppeteer 六路由預渲染產出 dist/
npm run build:no-prerender # 僅執行 type-check + vite build（跳過預渲染）
npm run preview          # 預覽 build 後產物
npm run test:unit -- --run # 單次執行 Vitest 單元與整合測試
npm run test:e2e         # Playwright E2E（首次需先執行 npx --no-install playwright install chromium）
```

> 後端啟動見 [backend api_docs.md](../../../backend/docs/api_docs.md) 文件首段。

---

## 注意事項

- `npm run build` 跑 `type-check` 與 `build-only` **並行**；TS 型別錯誤會讓 build 整體失敗，即使 `vite build` 本身成功。Build 前先單跑 `npm run type-check`。
- `services/funds.ts` 的 `pick_random_stock()` 對空 array 與索引越界都會 throw，避免 `tsconfig` 的 `noUncheckedIndexedAccess` 觸發 TS2322。
- 樣式集中在 `LuckyDraw.vue` 的 `<style scoped>`，色票 / 排版仍可獨立調整而不影響其他頁面。
- 字體優先 `Inter` 與 `Noto Sans TC`，未顯式 link Google Font；如需保證一致顯示可在 [index.html](../../index.html) 自行加 `<link>`。
