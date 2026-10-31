# 專案開源授權範圍、第三方資料來源限制與資產權利聲明 (Third-Party Notices & Licensing Status)

本文件說明 DestinyOrder 之專案開源授權適用範圍、公開版本庫內自有與第三方資產之權利盤點、第三方金融資料來源之公開條款查核結果，以及前後端相依套件之授權 Metadata 盤點。

---

## 1. 專案開源授權狀態（MIT License — 僅適用於公開之自有原創內容）

- **正式授權條款**：[**MIT License**](./LICENSE)
- **著作權聲明**：`Copyright (c) 2026 LaimoKarca`
- **授權適用範圍與邊界**：
  1. **公開之自有原創內容（適用根目錄 [`LICENSE`](./LICENSE) MIT 授權）**：專案擁有者（`LaimoKarca`）已正式確認本次納入公開版本庫之自有原創前後端程式碼、說明文件與專題文案（含 `AboutView.vue`、`FaqView.vue`）、合成示範資料產生器（`seed_demo_data.py`）、純幾何 SVG 與 Canvas 圖示（`favicon.svg`、`use_dice_favicon.ts`、`DiceIcon.vue`、`SlotIcon.vue`、`SpeakerButton.vue` 及 `AppMenu.vue` 之 `icon-chart`）以及 Web Audio API 即時音效合成邏輯（`audio.ts`、`LuckyDraw.vue`、`SlotMachine.vue`）均具備原創權利，並依根目錄 [`LICENSE`](./LICENSE)（MIT License）公開授權。
  2. **第三方元件、圖示、鷹架與相依套件（保留各自原始授權條款）**：本專案所引用之第三方內嵌圖示（如 `AppMenu.vue` 中源自 Feather Icons 之三個圖示）、初始專案鷹架設定檔（合理推測源自 `create-vue` 模板）以及所有前後端第三方開源套件，**各自保留其上游原始授權條款與著作權聲明**，不因本專案採用 MIT License 而改變其上游條款。
  3. **已排除之本機非必要腳本、媒體資產與金融資料集（不在本次公開與授權範圍內）**：凡透過 `.gitignore` 排除而未納入公開版本庫之本機項目（包含非必要離線腳本 `scripts/generate_favicon.py` 與 `scripts/render_lottery_sfx.py`、點陣圖示、`og-image.png`、未確認權利之音訊檔 `One_Life_Left.*` 與 `COPY/*.mp3`、真實抓取之 `backend/data/` ETF/TWSE 資料集及本機備份檔），**一律不屬於本次公開發布範圍，專案擁有者之 MIT 授權確認亦不擴張至該等未發布內容**。

---

## 2. 第三方金融資料來源與禁止再散布聲明

本專案程式碼包含針對臺灣證券交易所（TWSE）與特定投信發行商公開網頁之解析邏輯，並於前端頁面提供官方來源連結供使用者自行查閱。本輪開源準備針對各來源網站公開條款之查核結果如下（**本輪未能確認適用於這些抓取後成分股快照與證券清單之公開再散布授權**）：

1. **臺灣證券交易所（TWSE）**（官方服務條款參考：<https://www.twse.com.tw/zh/terms/use.html>）：
   - 網站一般使用條款限制未經許可之自動化下載，並保留資料再散布權利（僅政府資料開放平臺明確授權之資料集例外；本專案使用之 ISIN 查詢端點未確認屬開放資料授權範圍）。
2. **ETF 發行投信官網（本輪未能確認適用於抓取後成分股快照之再散布授權）**：
   - **元大投信**（官方聲明參考：<https://www.yuantafunds.com/Anti-Fraud>）：官網具明確著作權保留聲明，未確認可再散布之公開資料集授權。
   - **統一投信**（官方網站參考：<https://www.ezmoney.com.tw/MyAccount>）：官方索引頁面記載網站內容未經同意不得轉載，惟本輪無法直接擷取完整條款頁；未能確認成分股快照之再散布授權。
   - **富邦投信**（官方網站參考：<https://www.fsit.com.tw>、<https://websys.fsit.com.tw>）：本輪無法直接擷取可讀之服務條款頁面，資料再散布條件維持未確認。
   - **凱基投信**（官方網站參考：<https://www.kgifund.com.tw>）：未查得針對抓取後成分股快照之公開再散布授權（基金公開說明書中之指數授權條款規範不同當事人，不得視為對本專案之資料集授權）。
   - **重要原則**：公開可見之網頁內容不等同於允許將抓取後之資料集打包再散布。

### 公開版本庫處置規範

- **嚴格排除真實抓取資料集**：`backend/data/` 下所有歷史與最新抓取之 ETF 成分股快照（`*.json`）及證券清單（`symbol.json`、`symbol.csv`）**一律透過 `.gitignore` 排除，禁止提交或散布至公開 Git 儲存庫**。
- **僅提供純合成示範資料**：公開版本庫僅提供 [`backend/scripts/seed_demo_data.py`](./backend/scripts/seed_demo_data.py)（及根目錄 CLI 轉發層 [`scripts/seed_demo_data.py`](./scripts/seed_demo_data.py)），於本機或容器初次初始化時動態產生固定歷史示範日期（`2000/01/03`）與名稱含「示範」之虛構公司（`DEMO1`～`DEMO6`），供驗證程式邏輯與介面互動。
- **保留官方來源連結與標示**：前端權重查詢與各 ETF 說明保留指向發行商官方頁面的連結，方便使用者直接前往官方管道核對最新資訊。

---

## 3. 專案內靜態、圖示、音效、字型與鷹架資產權利狀態盤點

為確保公開版本庫權利邊界清晰，所有靜態資產、內嵌圖示、音效合成邏輯、字型引用與專案鷹架均依以下分類管理：

| 資產路徑 / 類別 | 來源與權利狀態分類 | 公開與建置處置 |
| :--- | :--- | :--- |
| **`frontend/src/components/AppMenu.vue`**<br>內嵌 3 個 SVG 圖示：<br>- `icon-list` (L346)<br>- `icon-about` (L356)<br>- `icon-faq` (L362) | **第三方開源圖示（Feather Icons，MIT License）**<br>經核對上游官方 [`feathericons/feather`](https://github.com/feathericons/feather)（`main/icons/list.svg`、`info.svg`、`help-circle.svg`），此三個內嵌 `data:image/svg+xml` 之幾何路徑完全一致。上游授權為 **MIT License (`Copyright (c) 2013-2023 Cole Bemis`)**。 | 保留於 `AppMenu.vue`，並於本文件**附錄 A** 完整保留上游 Feather Icons MIT 授權聲明原文（該聲明僅適用於此三個第三方圖示，與本專案根目錄 `LICENSE` 分別獨立） |
| `frontend/public/favicon.svg`<br>`frontend/src/composables/use_dice_favicon.ts`<br>`frontend/src/components/DiceIcon.vue`<br>`frontend/src/components/SlotIcon.vue`<br>`frontend/src/components/SpeakerButton.vue`<br>`frontend/src/components/AppMenu.vue` (`icon-chart`, L351) | `owner_confirmed_original; licensed_under_project_MIT`<br>（皆為純幾何 SVG 標籤或 HTML5 `<canvas>` 2D 座標繪製，無外部圖片或字型檔引用；專案擁有者 `LaimoKarca` 已確認原創權利並納入根目錄 [`LICENSE`](./LICENSE) MIT 授權） | 納入公開版本庫，依根目錄 [`LICENSE`](./LICENSE)（MIT License，`Copyright (c) 2026 LaimoKarca`）授權 |
| `frontend/src/stores/audio.ts`<br>`frontend/src/views/LuckyDraw.vue`<br>`frontend/src/views/SlotMachine.vue` | `owner_confirmed_original; licensed_under_project_MIT`<br>（執行期抽籤與拉霸音效 100% 由瀏覽器原生 Web Audio API 振盪器與數學雜訊緩衝區即時合成，不載入任何外部音訊檔；專案擁有者 `LaimoKarca` 已確認原創權利並納入根目錄 [`LICENSE`](./LICENSE) MIT 授權） | 納入公開版本庫，依根目錄 [`LICENSE`](./LICENSE)（MIT License，`Copyright (c) 2026 LaimoKarca`）授權 |
| `scripts/generate_favicon.py`<br>`scripts/render_lottery_sfx.py` | `non_essential_offline_scripts; excluded_not_published`<br>（非執行期必要之離線點陣圖生成與 WAV 渲染腳本，未納入本次公開授權確認範圍） | **維持排除**：保留於本機磁碟不刪除，由 `.gitignore` 排除於公開版本庫之外（不將擁有者之公開授權確認擴張至此二未發布腳本） |
| `frontend/public/favicon.ico`<br>`frontend/public/favicon-*.png`<br>`frontend/public/apple-touch-icon.png` | `generated_raster_icons; excluded_not_published`<br>（點陣圖示由本機離線腳本輸出，未納入本次公開發布與授權範圍） | **維持排除**：保留於本機磁碟，列入 `.gitignore` 與 `vite.config.ts` / `.dockerignore` 排除，不打進公開版本庫與 `dist/` |
| `COPY/*.mp3` | `local_audio_provenance_unconfirmed; excluded_not_published`<br>（本機 MP3 副本與離線腳本之對應關係及權利未確認，未納入本次公開與授權範圍） | **維持排除**：保留於本機磁碟並由 `.gitignore` 排除 |
| `frontend/public/audio/One_Life_Left.m4a`<br>`frontend/public/audio/One_Life_Left.mp3` | `unknown_third_party_audio_rights_unverified (do_not_redistribute)` | **禁止再散布**：保留於本機磁碟不刪除，由 `.gitignore`、`vite.config.ts` 與 `.dockerignore` 排除；前端預設不載入任何背景音樂 |
| `frontend/public/og-image.png` | `unverified_origin_and_legacy_branding (do_not_redistribute)` | **禁止再散布**：保留於本機磁碟不刪除，由 `.gitignore`、`vite.config.ts` 與 `.dockerignore` 排除，並自 `index.html` 移除引用 |
| **前端字型（System Font Stack）** | `css_font_family_reference_only; no_font_files_distributed`<br>（前端 CSS 僅指定 `'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif` 等系統字型家族名稱，未載入外部字型 CDN，原始碼樹亦未散布任何 `.ttf`/`.otf`/`.woff*` 字型檔） | 僅引用字型家族名稱，未散布任何字型檔案 |
| **前端專案初始鷹架設定檔**<br>（`frontend/tsconfig*.json`、`env.d.ts`、`.editorconfig` 等） | `inferred_create_vue_template; original_version_unverified`<br>（結構合理推測源自官方 [`vuejs/create-vue`](https://github.com/vuejs/create-vue) 模板，惟本機最初建立時之原始 `create-vue` 版本未留存紀錄；依上游現行 [`LICENSE`](https://github.com/vuejs/create-vue/blob/main/LICENSE)，其 generator core 為 `MIT`、**templates 與產生檔案為 `CC0-1.0`**，不得以 generator core 之 MIT 直接推論模板為 MIT） | 僅作為基礎工具鏈組態，上游模板部分保留其原始條款狀態，本專案自有修改部分依根目錄 [`LICENSE`](./LICENSE) 授權 |
| `destinyorder-images.tar` | `local_docker_image_archive_590MB (do_not_publish)` | 本機 Docker 映像備份檔，保留於本機並由 `.gitignore` 排除 |

---

## 4. 前後端第三方開源套件與授權 Metadata 盤點

本專案透過標準套件定義檔管理第三方開源依賴（以下數據為本輪針對本機 `frontend/package-lock.json`、`backend/requirements.txt` 與已安裝 Python 虛擬環境之查核範圍）。**注意：第三方相依套件各自適用其上游開源授權（並非全部皆為 MIT 授權），本專案根目錄之 `LICENSE`（MIT）僅適用於本專案自有原創內容；套件 metadata 盤點僅為清單證據，不等同於完整法律授權合規證明。**

### 4.1 前端 Node.js 依賴（[`frontend/package.json`](./frontend/package.json)、[`frontend/package-lock.json`](./frontend/package-lock.json)，共 542 個 lock entries）

- **核心與工具依賴**：執行期依賴包含 `vue`、`vue-router`、`pinia`；開發、測試與預渲染依賴包含 `vite`、`typescript`、`vue-tsc`、`vitest`、`@vue/test-utils`、`@playwright/test`、`puppeteer`、`eslint`、`oxlint`、`prettier` 等。
- **授權分布與特殊條款項目**：
  - 除常見寬鬆授權（`MIT`、`Apache-2.0`、`ISC`、`BSD-2-Clause`、`BSD-3-Clause`、`0BSD`、`BlueOak-1.0.0`、`CC0-1.0`、`Unlicense`）外，亦包含：
    - `caniuse-lite`：**`CC-BY-4.0`**（含姓名標示要求）
    - `lightningcss`（含各平台對應套件）：**`MPL-2.0`**（弱 Copyleft 檔案級授權）
    - `argparse`：**`Python-2.0`**
  - `memorystream@0.3.1`：為 `package-lock.json` 中唯一未直接標示頂層 `license` 字串之項目，經核對其已安裝之 `package.json`（舊式 `licenses.type = "MIT"`）及隨附 `LICENSE` 檔案確認為 `MIT`。

### 4.2 後端 Python 依賴（[`backend/requirements.txt`](./backend/requirements.txt) 共 24 個套件鎖定；本機已安裝虛擬環境共 26 筆套件 metadata）

- **主要套件授權分類**：
  - **`MIT`**：`fastapi`、`pydantic`（及相關核心組件）、`beautifulsoup4` 等
  - **`Apache-2.0`**：`requests`、`playwright`（`1.60.0`）等
  - **`BSD-3-Clause`**：`uvicorn`、`starlette`、`lxml`（`6.1.1`）等
  - **`MPL-2.0`**：`certifi`
  - **`MIT AND PSF-2.0`**：`greenlet`（`3.5.1`）
  - **`PSF-2.0`**：`typing_extensions`
  - **本機額外已安裝套件說明**：本機虛擬環境另含 `pillow`（`MIT-CMU`，僅供已透過 `.gitignore` 排除之本機離線腳本 `scripts/generate_favicon.py` 使用，未列入 `backend/requirements.txt` 之 24 個核心後端依賴中）。

### 4.3 散布範圍與未來合規義務提醒

- **原始碼版本庫範圍**：公開候選版本庫（Source Repository）已透過 `.gitignore` 排除 `node_modules/`、`venv/` 與 `frontend/dist/`，不直接散布第三方編譯二進位檔或打包產物；內建發布前盤點腳本 [`scripts/audit_publication.py`](./scripts/audit_publication.py) 預設不含任何私人 hostname 或特定驗證碼常數（若維護者需於本機掃描特定私有網域，可透過可選環境變數 `DESTINYORDER_AUDIT_PRIVATE_HOSTS` 傳入逗號分隔清單）。
- **未來散布 Bundle 或容器映像之義務**：若未來對外發布預先建置之前端靜態產物（`dist/`）或 Docker 容器映像（Images，含 Dockerfile 透過 Debian `apt-get` 安裝之 `fonts-noto-cjk` / `fonts-noto-color-emoji` 等系統套件），散布者必須保留各上游套件要求之 `LICENSE` / `NOTICE` 聲明與屬性標示（特別注意 `Apache-2.0`、`MPL-2.0`、`CC-BY-4.0`、`BSD`、`PSF-2.0`、`SIL OFL 1.1` 等條款義務），並逐一核對隨附義務。

---

## 附錄 A：Feather Icons 上游授權聲明原文（僅適用於 `AppMenu.vue` 三個內嵌第三方圖示）

> **適用範圍限制聲明**：以下 MIT License 原文（`Copyright (c) 2013-2023 Cole Bemis`）**僅適用於** [`frontend/src/components/AppMenu.vue`](./frontend/src/components/AppMenu.vue) 中引用自上游 [Feather Icons](https://github.com/feathericons/feather) 之三個內嵌第三方 SVG 圖示（`icon-list`、`icon-about`、`icon-faq`，對應上游 `icons/list.svg`、`icons/info.svg`、`icons/help-circle.svg`）；DestinyOrder 專案本身公開之自有原創內容則另依專案根目錄 [`LICENSE`](./LICENSE)（`Copyright (c) 2026 LaimoKarca`）授權。

```text
The MIT License (MIT)

Copyright (c) 2013-2023 Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
