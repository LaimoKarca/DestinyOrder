<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { DrawableStock } from '@/types/funds'
import { use_funds_store } from '@/stores/funds'

const ETF_ORDER = ['0050', '006208', '009816', '00403A', '00981A'] as const

const store = use_funds_store()
const { stocks, etf_codes, data_date, loading, error } = storeToRefs(store)

const search = ref('')

// ---- Industry searchable combobox state ----
const industry_filter = ref('')
const industry_query = ref('')
const industry_open = ref(false)
const industry_highlighted = ref(-1)
const industry_combo_ref = ref<HTMLElement | null>(null)
const industry_list_ref = ref<HTMLElement | null>(null)

// ---- ETF multi-select dropdown state ----
const etf_filter = ref<Set<string>>(new Set())
const etf_open = ref(false)
const etf_combo_ref = ref<HTMLElement | null>(null)

onMounted(() => {
  store.ensure_loaded()
  document.addEventListener('mousedown', on_doc_mousedown)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', on_doc_mousedown)
})

function on_doc_mousedown(e: MouseEvent): void {
  const target = e.target as Node | null
  if (
    industry_open.value &&
    industry_combo_ref.value &&
    target &&
    !industry_combo_ref.value.contains(target)
  ) {
    close_industry_dropdown()
  }
  if (
    etf_open.value &&
    etf_combo_ref.value &&
    target &&
    !etf_combo_ref.value.contains(target)
  ) {
    etf_open.value = false
  }
}

// ---- Industry combobox handlers ----

function open_industry_dropdown(): void {
  industry_open.value = true
  industry_highlighted.value = industry_filter.value ? 0 : -1
}

function close_industry_dropdown(): void {
  industry_open.value = false
  if (industry_query.value !== industry_filter.value) {
    industry_query.value = industry_filter.value
  }
}

function select_industry(name: string): void {
  industry_filter.value = name
  industry_query.value = name
  industry_open.value = false
}

function clear_industry(): void {
  industry_filter.value = ''
  industry_query.value = ''
  industry_open.value = false
}

function on_industry_input(): void {
  industry_open.value = true
  industry_highlighted.value = 0
}

function on_industry_keydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    close_industry_dropdown()
    e.preventDefault()
    return
  }
  if (!industry_open.value) {
    if (e.key === 'ArrowDown' || e.key === 'Enter') {
      open_industry_dropdown()
      e.preventDefault()
    }
    return
  }
  const opts = displayed_industries.value
  if (e.key === 'ArrowDown') {
    industry_highlighted.value = Math.min(opts.length - 1, industry_highlighted.value + 1)
    e.preventDefault()
  } else if (e.key === 'ArrowUp') {
    industry_highlighted.value = Math.max(-1, industry_highlighted.value - 1)
    e.preventDefault()
  } else if (e.key === 'Enter') {
    if (industry_highlighted.value === -1) {
      clear_industry()
    } else {
      const picked = opts[industry_highlighted.value]
      if (picked) select_industry(picked)
    }
    e.preventDefault()
  }
}

// ---- ETF dropdown handlers ----

function toggle_etf(code: string): void {
  const next = new Set(etf_filter.value)
  if (next.has(code)) next.delete(code)
  else next.add(code)
  etf_filter.value = next
}

function clear_etf(): void {
  etf_filter.value = new Set()
}

const etf_display = computed(() => {
  const n = etf_filter.value.size
  if (n === 0) return '全部 ETF'
  if (n <= 2) {
    return ETF_ORDER.filter((c) => etf_filter.value.has(c)).join('、')
  }
  return `已選 ${n} 檔 ETF`
})

const ordered_etfs = computed(() => {
  // 依固定順序顯示，而非 API 回傳的順序
  return ETF_ORDER.filter((code) => etf_codes.value.includes(code))
})

function clear_filters(): void {
  search.value = ''
  clear_industry()
  clear_etf()
}

// ---- Computed ----

const industries = computed(() => {
  const set = new Set<string>()
  for (const s of stocks.value) {
    if (s.industry) set.add(s.industry)
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b))
})

const displayed_industries = computed(() => {
  const q = industry_query.value.trim().toLowerCase()
  if (!q || q === industry_filter.value.toLowerCase()) return industries.value
  return industries.value.filter((ind) => ind.toLowerCase().includes(q))
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  const ef = etf_filter.value

  const rows = stocks.value.filter((s) => {
    if (q) {
      const name_hit = s.name.toLowerCase().includes(q)
      const symbol_hit = (s.symbol ?? '').toLowerCase().includes(q)
      if (!name_hit && !symbol_hit) return false
    }
    if (industry_filter.value && s.industry !== industry_filter.value) {
      return false
    }
    if (ef.size > 0) {
      const codes = new Set(s.sources.map((x) => x.etf_code))
      let any = false
      for (const code of ef) {
        if (codes.has(code)) {
          any = true
          break
        }
      }
      if (!any) return false
    }
    return true
  })

  rows.sort((a, b) => {
    if (b.sources.length !== a.sources.length) {
      return b.sources.length - a.sources.length
    }
    return a.name.localeCompare(b.name)
  })

  return rows
})

const has_active_filters = computed(
  () =>
    search.value.trim() !== '' ||
    industry_filter.value !== '' ||
    etf_filter.value.size > 0,
)

function sorted_sources(stock: DrawableStock) {
  return [...stock.sources].sort(
    (a, b) =>
      ETF_ORDER.indexOf(a.etf_code as (typeof ETF_ORDER)[number]) -
      ETF_ORDER.indexOf(b.etf_code as (typeof ETF_ORDER)[number]),
  )
}

watch(industry_highlighted, async (idx) => {
  if (!industry_list_ref.value) return
  await Promise.resolve()
  const items = industry_list_ref.value.querySelectorAll<HTMLElement>('.combo-item')
  const target = items[idx + 1]
  target?.scrollIntoView({ block: 'nearest' })
})
</script>

<template>
  <main class="page">
    <div class="aurora" aria-hidden="true"></div>

    <header class="hero">
      <h1>五檔 ETF 持股表</h1>
    </header>

    <section class="stage">
      <div v-if="loading && stocks.length === 0" class="state state-loading">
        <div class="spinner" />
        <p>載入最新基金成分股…</p>
      </div>

      <div v-else-if="error" class="state state-error">
        <p>⚠️ {{ error }}</p>
        <p class="hint">請確認後端服務已啟動、資料夾 backend/data/funds 存在。</p>
      </div>

      <template v-else>
        <div class="card">
          <div class="filters">
            <label class="filter filter-search">
              <span class="filter-label filter-label--search"></span>
              <div class="search-wrapper">
                <input
                  v-model="search"
                  type="search"
                  placeholder="代號或名稱…"
                  autocomplete="off"
                />
                <span class="filter-meta">
                  <button
                    v-if="has_active_filters"
                    type="button"
                    class="clear-inline"
                    @click="clear_filters"
                  >
                    清除篩選
                  </button>
                  <span class="meta-text">
                    <strong>{{ filtered.length }}</strong> /
                    {{ stocks.length }}
                  </span>
                </span>
              </div>
            </label>

            <div ref="industry_combo_ref" class="filter filter-industry">
              <div class="combo" :class="{ 'is-open': industry_open }">
                <input
                  v-model="industry_query"
                  type="text"
                  placeholder="全部產業"
                  autocomplete="off"
                  role="combobox"
                  aria-autocomplete="list"
                  :aria-expanded="industry_open"
                  @focus="open_industry_dropdown"
                  @click="open_industry_dropdown"
                  @input="on_industry_input"
                  @keydown="on_industry_keydown"
                />
                <button
                  v-if="industry_filter || industry_query"
                  type="button"
                  class="combo-clear"
                  aria-label="清空產業篩選"
                  @mousedown.prevent="clear_industry"
                >
                  ✕
                </button>
                <span class="combo-caret" aria-hidden="true">▾</span>
                <Transition name="combo">
                  <ul
                    v-if="industry_open"
                    ref="industry_list_ref"
                    class="combo-list"
                    role="listbox"
                  >
                    <li
                      class="combo-item combo-item-clear"
                      :class="{ 'is-highlighted': industry_highlighted === -1 }"
                      role="option"
                      :aria-selected="industry_filter === ''"
                      @mousedown.prevent="clear_industry"
                    >
                      全部產業
                    </li>
                    <li v-if="displayed_industries.length === 0" class="combo-empty">
                      無符合產業
                    </li>
                    <li
                      v-for="(opt, idx) in displayed_industries"
                      :key="opt"
                      class="combo-item"
                      :class="{
                        'is-highlighted': industry_highlighted === idx,
                        'is-selected': industry_filter === opt,
                      }"
                      role="option"
                      :aria-selected="industry_filter === opt"
                      @mousedown.prevent="select_industry(opt)"
                    >
                      {{ opt }}
                    </li>
                  </ul>
                </Transition>
              </div>
            </div>

            <div ref="etf_combo_ref" class="filter filter-etf">
              <div class="combo" :class="{ 'is-open': etf_open }">
                <button
                  type="button"
                  class="combo-trigger"
                  :class="{ 'is-placeholder': etf_filter.size === 0 }"
                  :aria-expanded="etf_open"
                  @click="etf_open = !etf_open"
                >
                  <span class="combo-display">{{ etf_display }}</span>
                  <span class="combo-caret" aria-hidden="true">▾</span>
                </button>
                <Transition name="combo">
                  <ul v-if="etf_open" class="combo-list" role="listbox" aria-multiselectable="true">
                    <li
                      class="combo-item combo-item-clear"
                      role="option"
                      :aria-selected="etf_filter.size === 0"
                      @mousedown.prevent="clear_etf"
                    >
                      全部 ETF
                    </li>
                    <li
                      v-for="code in ordered_etfs"
                      :key="code"
                      class="combo-item combo-item-check"
                      :class="{ 'is-selected': etf_filter.has(code) }"
                      role="option"
                      :aria-selected="etf_filter.has(code)"
                      @mousedown.prevent="toggle_etf(code)"
                    >
                      <span class="check-box" aria-hidden="true">
                        <span v-if="etf_filter.has(code)">✓</span>
                      </span>
                      <span class="combo-item-text">{{ code }}</span>
                    </li>
                  </ul>
                </Transition>
              </div>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="col-code">股票代號</th>
                  <th class="col-name">名稱</th>
                  <th class="col-industry">產業別</th>
                  <th class="col-sources">
                    選股陣容
                    <span class="th-hint">（持有此股的 ETF）</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="filtered.length === 0">
                  <td colspan="4" class="state-row">
                    {{ stocks.length === 0 ? '尚無資料' : '沒有符合條件的標的' }}
                  </td>
                </tr>
                <tr v-for="stock in filtered" v-else :key="stock.name">
                  <td class="col-code">{{ stock.symbol ?? '——' }}</td>
                  <td class="col-name">{{ stock.name }}</td>
                  <td class="col-industry">{{ stock.industry ?? '未分類' }}</td>
                  <td class="col-sources">
                    <span class="source-tags">
                      <span
                        v-for="src in sorted_sources(stock)"
                        :key="src.etf_code"
                        class="tag"
                        :title="`${src.etf_name} · 權重 ${src.weight}`"
                      >
                        {{ src.etf_code }}
                      </span>
                    </span>
                  </td>
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
  padding: clamp(0.75rem, 2.5vw, 2.25rem) clamp(1rem, 4vw, 3rem)
    var(--app-footer-height);
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
    radial-gradient(
      circle at 50% 0%,
      rgba(124, 92, 255, 0.18),
      transparent 50%
    ),
    radial-gradient(
      circle at 80% 90%,
      rgba(83, 196, 255, 0.12),
      transparent 50%
    );
  pointer-events: none;
}

.hero {
  position: relative;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  padding-left: clamp(0, 6vw, 4rem);
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

.stage {
  position: relative;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  /* 吃掉 hero 之後的所有垂直空間，讓內層表格成為唯一可滾動區域 */
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
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
  padding: clamp(0.5rem, 1.75vw, 0.9rem);
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
  gap: 0.9rem;
  /* 占滿 stage 剩餘空間，讓內層 table-wrap 可以 flex:1 撐開 */
  flex: 1;
  min-height: 0;
}

/* ---------- 篩選列：單列 grid，三欄並排 ---------- */

.filters {
  display: grid;
  grid-template-columns: minmax(180px, 1.6fr) minmax(150px, 1fr) minmax(150px, 1fr);
  align-items: end;
  gap: 0.5rem 0.9rem;
}
.filter {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}
.filter-label {
  font-size: 0.68rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #8a8fae;
}

/* 搜尋欄 label：flex 容器，input 占滿寬度，meta 靠右 */
.filter-search {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.filter-label--search {
  display: none;
}

.search-wrapper input {
  width: 100%;
  padding-right: 12rem;
}

.filter-meta {
  position: absolute;
  right: 0.75rem;
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  font-size: 0.72rem;
  letter-spacing: 0;
  text-transform: none;
  color: #8a8fae;
  white-space: nowrap;
  flex-shrink: 0;
  pointer-events: none;
}

.filter-meta button {
  pointer-events: auto;
}
.filter-meta .meta-text {
  white-space: nowrap;
}
.filter-meta strong {
  color: #8a8fae;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.clear-inline {
  padding: 0.18rem 0.6rem;
  font-size: 0.68rem;
  font-family: inherit;
  letter-spacing: 0.02em;
  color: #c9cce8;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  cursor: pointer;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}
.clear-inline:hover {
  background: rgba(255, 122, 200, 0.2);
  color: #fff;
  border-color: transparent;
}
.filter input,
.combo input,
.combo-trigger {
  width: 100%;
  padding: 0.55rem 0.75rem;
  font-size: 0.92rem;
  font-family: inherit;
  color: #e8eaf6;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  outline: none;
  transition:
    border-color 0.2s ease,
    background 0.2s ease;
}
.filter input::placeholder,
.combo input::placeholder {
  color: #6e7396;
}
.filter input:focus,
.combo input:focus,
.combo-trigger:focus-visible {
  border-color: rgba(179, 184, 255, 0.55);
  background: rgba(255, 255, 255, 0.08);
}

/* ---------- combobox 通用 ---------- */

.combo {
  position: relative;
}
.combo input,
.combo-trigger {
  padding-right: 2.4rem;
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
.combo-clear {
  position: absolute;
  right: 1.7rem;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #c9cce8;
  font-size: 0.62rem;
  cursor: pointer;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}
.combo-clear:hover {
  background: rgba(255, 122, 200, 0.3);
  color: #fff;
}

.combo-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  cursor: pointer;
  text-align: left;
  -webkit-tap-highlight-color: transparent;
}
.combo-trigger.is-placeholder .combo-display {
  color: #6e7396;
}
.combo-display {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
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
  font-size: 0.88rem;
  color: #d8dbf3;
  border-radius: 8px;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.combo-item:hover,
.combo-item.is-highlighted {
  background: rgba(126, 200, 255, 0.18);
  color: #fff;
}
.combo-item.is-selected {
  color: #b3b8ff;
  font-weight: 700;
}
.combo-item-clear {
  font-size: 0.78rem;
  color: #8a8fae;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px 8px 0 0;
  margin-bottom: 0.2rem;
}
.combo-item-check {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  font-variant-numeric: tabular-nums;
}
.check-box {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.72rem;
  color: transparent;
  flex-shrink: 0;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}
.combo-item-check.is-selected .check-box {
  background: linear-gradient(135deg, #b3b8ff, #7ec8ff);
  color: #0b0f24;
  border-color: transparent;
}
.combo-empty {
  padding: 0.6rem 0.7rem;
  font-size: 0.82rem;
  color: #6e7396;
  text-align: center;
}

/* ---------- 表格 ---------- */

.table-wrap {
  /* 把 card 內剩餘空間全吃掉，內部 scroll；同時是頁面唯一垂直 scroll 來源 */
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
  font-size: 1.104rem;
}
thead th,
tbody td {
  text-align: center;
}
/* 選股陣容欄維持靠左對齊 */
thead th.col-sources,
tbody td.col-sources {
  text-align: left;
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
}
.th-hint {
  display: inline-block;
  margin-left: 0.3rem;
  font-size: 0.64rem;
  font-weight: 400;
  letter-spacing: 0.08em;
  text-transform: none;
  color: #5e6285;
}

tbody td {
  padding: 0.7rem 0.7rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}
tbody tr:hover td {
  background: rgba(126, 200, 255, 0.06);
}

/* ---------- 欄位寬度與資料列淡字樣式 ---------- */

.col-code {
  min-width: 7.15em; /* 加寬 10% */
}
.col-name {
  min-width: 9.75em; /* 加寬 30% */
}
.col-industry {
  min-width: 11.7em; /* 加寬 30% */
}
.col-sources {
  /* 用 100% 把剩餘水平空間全吃下，逼前三欄停在 min-width */
  width: 100%;
}

/* 將資料列變為白色 */
tbody td.col-code,
tbody td.col-name,
tbody td.col-industry {
  white-space: nowrap;
  color: #e8eaf6;
  font-weight: 400;
  font-size: 1.104rem;
}

.source-tags {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.tag {
  padding: 0.2rem 0.5rem;
  font-size: 0.864rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #e2e6ff;
  background: linear-gradient(
    135deg,
    rgba(126, 200, 255, 0.22),
    rgba(124, 92, 255, 0.22)
  );
  border: 1px solid rgba(179, 184, 255, 0.32);
  border-radius: 6px;
  font-variant-numeric: tabular-nums;
}
.state-row {
  padding: 2rem;
  text-align: center;
  color: #8a8fae;
}

/* ---------- 免責 ---------- */

.disclaimer {
  margin: 0;
  text-align: center;
  font-size: clamp(0.72rem, 2.4vw, 0.78rem);
  color: #6e7396;
  line-height: 1.6;
  flex-shrink: 0;
}

/* ---------- RWD ---------- */

@media (max-width: 768px) {
  .hero {
    padding-left: 0;
  }
}

@media (max-width: 720px) {
  .filters {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 540px) {
  /* 表格字體統一對齊上方篩選欄（0.92rem） */
  table {
    font-size: 0.92rem;
  }
  thead th {
    padding: 0.5rem 0.5rem;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
  }
  tbody td {
    padding: 0.45rem 0.5rem;
  }
  /* 股票代號 / 名稱 / 產業：以該欄最長的文字為基準（shrink-to-fit）；
     剩餘水平空間由 col-sources（width:100%）吸收 */
  .col-code,
  .col-name,
  .col-industry {
    min-width: 0;
    width: 1%;
    white-space: nowrap;
  }
  tbody td.col-code,
  tbody td.col-name,
  tbody td.col-industry {
    font-size: 0.92rem;
  }
  .th-hint {
    display: none;
  }
  /* 選股陣容：強制單列，列高才不會被多顆 tag 撐高；
     超出部分由外層 .table-wrap 既有的橫向滾動承接 */
  .source-tags {
    flex-wrap: nowrap;
    gap: 0.28rem;
  }
  .tag {
    padding: 0.2rem 0.5rem;
    font-size: 0.82rem;
    flex-shrink: 0;
  }
  /* 手機版免責聲明併為一段，不強制換行 */
  .disclaimer-break {
    display: none;
  }
}

/* 視窗高度太矮時，放開 100vh 鎖定，避免內容被壓扁 */
@media (max-height: 620px) {
  .page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }
  .table-wrap {
    max-height: 60vh;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner,
  .combo-enter-active,
  .combo-leave-active {
    animation: none !important;
    transition: none !important;
  }
}
</style>