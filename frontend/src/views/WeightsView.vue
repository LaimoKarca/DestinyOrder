<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { EtfDetail, FundsByEtfResponse } from '@/types/funds'
import { fetch_funds_by_etf } from '@/services/funds'

const loading = ref(false)
const error = ref<string | null>(null)
const data_date = ref('')
const etfs = ref<EtfDetail[]>([])

const selected_code = ref<string>('')

// 下拉選單狀態
const dropdown_open = ref(false)
const dropdown_ref = ref<HTMLElement | null>(null)

const current_etf = computed<EtfDetail | null>(() => {
  if (!selected_code.value) return etfs.value[0] ?? null
  return etfs.value.find((e) => e.code === selected_code.value) ?? null
})

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const payload: FundsByEtfResponse = await fetch_funds_by_etf()
    etfs.value = payload.etfs
    data_date.value = payload.date
    if (payload.etfs.length > 0 && !selected_code.value) {
      selected_code.value = payload.etfs[0]!.code
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function on_doc_mousedown(e: MouseEvent): void {
  if (!dropdown_open.value) return
  const target = e.target as Node | null
  if (dropdown_ref.value && target && !dropdown_ref.value.contains(target)) {
    dropdown_open.value = false
  }
}

function pick(code: string): void {
  selected_code.value = code
  dropdown_open.value = false
}

onMounted(() => {
  void load()
  document.addEventListener('mousedown', on_doc_mousedown)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', on_doc_mousedown)
})
</script>

<template>
  <main class="page">
    <div class="aurora" aria-hidden="true"></div>

    <header class="hero">
      <h1>成分股權重查詢</h1>
      <p class="subtitle">
        選一檔 ETF，立刻看完整持股與權重；<br class="br-mobile-only" />資料每日由官方來源自動更新。
      </p>
    </header>

    <section class="stage">
      <div v-if="loading && etfs.length === 0" class="state state-loading">
        <div class="spinner" />
        <p>載入 ETF 明細…</p>
      </div>

      <div v-else-if="error" class="state state-error">
        <p>⚠️ {{ error }}</p>
        <p class="hint">請確認後端服務已啟動、資料夾 backend/data/funds 存在。</p>
      </div>

      <template v-else-if="current_etf">
        <div class="card">
          <!-- 上方：下拉 + 名稱 + 更新日 -->
          <div class="meta-row">
            <div ref="dropdown_ref" class="meta-cell meta-cell-select">
              <span class="meta-label">ETF 代號</span>
              <div class="combo" :class="{ 'is-open': dropdown_open }">
                <button
                  type="button"
                  class="combo-trigger"
                  :aria-expanded="dropdown_open"
                  @click="dropdown_open = !dropdown_open"
                >
                  <span class="combo-display">{{ current_etf.code }}</span>
                  <span class="combo-caret" aria-hidden="true">▾</span>
                </button>
                <Transition name="combo">
                  <ul v-if="dropdown_open" class="combo-list" role="listbox">
                    <li
                      v-for="etf in etfs"
                      :key="etf.code"
                      class="combo-item"
                      :class="{ 'is-selected': etf.code === current_etf.code }"
                      role="option"
                      :aria-selected="etf.code === current_etf.code"
                      @mousedown.prevent="pick(etf.code)"
                    >
                      {{ etf.code }}
                    </li>
                  </ul>
                </Transition>
              </div>
            </div>

            <div class="meta-cell meta-cell-name">
              <span class="meta-label">ETF 名稱</span>
              <span class="meta-value">{{ current_etf.name }}</span>
            </div>

            <div class="meta-cell meta-cell-date">
              <span class="meta-label">資料日期</span>
              <span class="meta-value mono">{{ current_etf.update_time }}</span>
            </div>
          </div>

          <!-- 來源連結 + 提醒 -->
          <div class="source-row">
            <a
              :href="current_etf.source_url"
              class="source-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span class="source-icon" aria-hidden="true">↗</span>
              <span class="source-text">{{ current_etf.source_url }}</span>
            </a>
            <p class="source-hint">
              ※ 本頁資料由程式定期自官方來源抓取，與來源網址可能有時間落差；一切數據請以上方官方來源為準。
            </p>
          </div>

          <!-- 持股表 -->
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="col-code">個股代號</th>
                  <th class="col-name">名稱</th>
                  <th class="col-weight">權重</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="current_etf.holdings.length === 0">
                  <td colspan="3" class="state-row">尚無持股資料</td>
                </tr>
                <tr
                  v-for="(h, i) in current_etf.holdings"
                  v-else
                  :key="`${current_etf.code}-${h.name}-${i}`"
                >
                  <td class="col-code mono">{{ h.symbol ?? '—' }}</td>
                  <td class="col-name">{{ h.name }}</td>
                  <td class="col-weight mono">{{ h.weight }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p class="disclaimer">
          ※ 本工具僅供研究參考，不構成任何投資建議；實際投資決策請審慎評估。<br class="disclaimer-break" /><template
            v-if="data_date"
            >資料抓取日期 {{ data_date }}（各 ETF 實際公告時間不同）。</template
          >
        </p>
      </template>
    </section>
  </main>
</template>

<style scoped>
.page {
  position: relative;
  /* 鎖定為視窗高度，內層表格自己 scroll，避免雙層 scroll bar */
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  /* 底部保留固定 footer 的空間，避免免責文字被遮蔽 */
  padding: clamp(1.5rem, 5vw, 4.5rem) clamp(1rem, 4vw, 3rem)
    calc(var(--app-footer-height) + clamp(0.6rem, 2vw, 1.2rem));
  color: #e8eaf6;
  font-family:
    'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif;
  background:
    radial-gradient(1200px 600px at 10% -20%, #2a1f6b 0%, transparent 60%),
    radial-gradient(900px 500px at 110% 10%, #1e4778 0%, transparent 55%),
    linear-gradient(180deg, #0b0f24 0%, #070a1a 100%);
  display: flex;
  flex-direction: column;
  gap: clamp(0.6rem, 1.5vw, 1rem);
}

.aurora {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 0%, rgba(124, 92, 255, 0.18), transparent 50%),
    radial-gradient(
      circle at 80% 90%,
      rgba(83, 196, 255, 0.12),
      transparent 50%
    );
  pointer-events: none;
}

/* ---------- Hero ---------- */

.hero {
  position: relative;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  text-align: center;
  flex-shrink: 0;
}
.hero h1 {
  margin: 0 0 0.5rem;
  font-size: clamp(1.75rem, 6vw, 3.2rem);
  font-weight: 800;
  letter-spacing: 0.02em;
  background: linear-gradient(90deg, #fff 0%, #b3b8ff 60%, #7ec8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  line-height: 1.2;
}
.subtitle {
  margin: 0;
  font-size: clamp(0.86rem, 2.6vw, 1rem);
  color: #b1b6d6;
  line-height: 1.6;
}

/* ---------- Stage / Card ---------- */

.stage {
  position: relative;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.state {
  text-align: center;
  padding: clamp(2rem, 8vw, 3rem) 1rem;
  color: #b1b6d6;
}
.state-error p:first-child {
  color: #ff9a9a;
  font-weight: 600;
}
.hint {
  margin-top: 0.4rem;
  font-size: 0.85rem;
  color: #8a8fae;
}
.spinner {
  width: 32px;
  height: 32px;
  margin: 0 auto 0.8rem;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.12);
  border-top-color: #8a7dff;
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.card {
  position: relative;
  border-radius: clamp(16px, 3vw, 22px);
  padding: clamp(0.8rem, 2.2vw, 1.2rem);
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.06) 0%,
    rgba(255, 255, 255, 0.02) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow:
    0 30px 60px -30px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex: 1;
  min-height: 0;
}

/* ---------- Meta row ---------- */

/* 桌機：三 cell 橫向 flex 填滿一列，每格 label 與 value 同行省空間 */
.meta-row {
  display: flex;
  gap: 1.4rem;
  align-items: center;
  width: 100%;
  text-align: center;
}
.meta-cell {
  flex: 1;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  min-width: 0;
}
.meta-label {
  flex-shrink: 0;
  font-size: 0.66rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #8a8fae;
}
.meta-value {
  /* 純展示文字，刻意不加底板/邊框，避免使用者誤以為可點 */
  flex: 1;
  min-width: 0;
  font-size: 1.05rem;
  color: #f0f2ff;
  font-weight: 700;
  padding: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}
.meta-cell-select {
  justify-content: center;
}
.meta-cell-select .combo {
  flex: 1;
  min-width: 0;
}
.meta-cell-name .meta-value {
  text-align: center;
}
.meta-cell-date {
  grid-column: 1 / -1;
}
.mono {
  font-variant-numeric: tabular-nums;
}

/* ---------- Combobox（下拉） ---------- */

.combo {
  position: relative;
}
.combo-trigger {
  width: 100%;
  padding: 0.55rem 0.75rem;
  padding-right: 2.4rem;
  font-size: 0.92rem;
  font-family: inherit;
  font-weight: 600;
  color: #e8eaf6;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  outline: none;
  transition:
    border-color 0.2s ease,
    background 0.2s ease;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  -webkit-tap-highlight-color: transparent;
}
.combo-trigger:hover,
.combo-trigger:focus-visible {
  border-color: rgba(179, 184, 255, 0.55);
  background: rgba(255, 255, 255, 0.08);
}
.combo-display {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  text-align: center;
}
.combo-caret {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #8a8fae;
  font-size: 0.7rem;
  pointer-events: none;
  transition: transform 0.2s ease;
}
.combo.is-open .combo-caret {
  transform: translateY(-50%) rotate(180deg);
  color: #b3b8ff;
}

.combo-list {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 20;
  max-height: 260px;
  overflow-y: auto;
  margin: 0;
  padding: 0.3rem;
  list-style: none;
  background: linear-gradient(
    180deg,
    rgba(20, 24, 48, 0.96) 0%,
    rgba(10, 12, 28, 0.97) 100%
  );
  border: 1px solid rgba(179, 184, 255, 0.22);
  border-radius: 12px;
  box-shadow: 0 24px 50px -16px rgba(0, 0, 0, 0.7);
}
.combo-enter-active,
.combo-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.22s cubic-bezier(0.22, 0.84, 0.32, 1);
}
.combo-enter-from,
.combo-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.combo-item {
  padding: 0.5rem 0.7rem;
  font-size: 0.92rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: #d8dbf3;
  border-radius: 8px;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.combo-item:hover {
  background: rgba(126, 200, 255, 0.18);
  color: #fff;
}
.combo-item.is-selected {
  color: #b3b8ff;
}

/* ---------- Source row ---------- */

.source-row {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.7rem 0.9rem;
  border-radius: 10px;
  background: rgba(126, 200, 255, 0.05);
  border: 1px dashed rgba(179, 184, 255, 0.22);
}
.source-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.88rem;
  color: #b3b8ff;
  text-decoration: none;
  word-break: break-all;
  font-weight: 500;
  transition: color 0.18s ease;
}
.source-link:hover {
  color: #fff;
  text-decoration: underline;
}
.source-icon {
  font-size: 0.85rem;
  color: #7ec8ff;
  flex-shrink: 0;
}
.source-text {
  min-width: 0;
}
.source-hint {
  margin: 0;
  font-size: 0.76rem;
  color: #8a8fae;
  line-height: 1.55;
}

/* ---------- Table ---------- */

.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 1rem;
}
thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 0.8rem 0.7rem;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #8a8fae;
  font-weight: 700;
  background: rgba(12, 16, 36, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  white-space: nowrap;
  text-align: center;
}
tbody td {
  padding: 0.7rem 0.7rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  text-align: center;
  color: #e8eaf6;
  vertical-align: middle;
}
tbody tr:hover td {
  background: rgba(126, 200, 255, 0.06);
}
/* 三欄等寬 + 置中對齊，視覺平衡 */
.col-code,
.col-name,
.col-weight {
  width: 33.33%;
}
.col-weight {
  font-weight: 700;
  color: #b3b8ff;
}
.state-row {
  padding: 2rem;
  text-align: center !important;
  color: #8a8fae;
}

/* ---------- Disclaimer ---------- */

.disclaimer {
  margin: 0;
  text-align: center;
  font-size: clamp(0.72rem, 2.4vw, 0.78rem);
  color: #6e7396;
  line-height: 1.6;
}

/* ---------- RWD ---------- */

.br-mobile-only {
  display: none;
}
.br-desktop-only {
  display: inline;
}

/* 手機：整體維持一列，日期區塊內部改為上下並排 */
@media (max-width: 540px) {
  .meta-row {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
    flex-wrap: nowrap;
  }
  .meta-cell {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 0.2rem;
    min-width: 0;
    width: auto;
  }
  .meta-label {
    display: none;
    font-size: 0.6rem;
    letter-spacing: 0.12em;
  }
  .meta-cell-select {
    flex: 0 0 28%; 
  }
  .meta-cell-name {
    flex: 1 1 auto;
    justify-content: center;
  }
  /* 修改此處：調整字體*/
  .meta-cell-name .meta-value {
    font-size: clamp(1rem, 4vw, 1.25rem);
    font-weight: 600;
    text-align: center; 
    padding: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    width: 100%;
  }
  .meta-cell-date {
    flex: 0 0 auto;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    gap: 0.15rem;
  }
  .meta-cell-date .meta-label {
    display: block;
    font-size: 0.55rem;
    letter-spacing: 0.1em;
    color: #8a8fae;
    line-height: 1;
  }
  .meta-cell-date .meta-value {
    font-size: 0.78rem;
    line-height: 1;
    padding: 0;
    white-space: nowrap;
    display: block;
  }
  .combo-trigger {
    padding: 0.4rem 0.55rem;
    padding-right: 1.6rem;
    font-size: 0.82rem;
    justify-content: center;
    width: 100%;
  }
  .combo-display {
    text-align: center;
  }
  .combo-caret {
    right: 0.5rem;
  }
  .br-desktop-only {
    display: none;
  }
  .br-mobile-only {
    display: inline;
  }
  table {
    font-size: 0.92rem;
  }
  thead th,
  tbody td {
    padding: 0.55rem 0.45rem;
  }
  /* 手機版免責聲明併為一段，不強制換行 */
  .disclaimer-break {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .combo-enter-active,
  .combo-leave-active {
    transition: none !important;
  }
  .spinner {
    animation-duration: 3s;
  }
}
</style>
