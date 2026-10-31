<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { DrawableStock } from '@/types/funds'
import { pick_random_stock } from '@/services/funds'
import { use_funds_store } from '@/stores/funds'
import { use_audio_store } from '@/stores/audio'

const ETF_ORDER = ['0050', '006208', '009816', '00403A', '00981A'] as const

// 拉霸機核心常數
const ITEM_HEIGHT = 88 // 單格高度（px）；同步 CSS 的 .reel-item / .reel-window
const REEL_DURATIONS = [1700, 2350, 3100] // 三軸停止時間差（ms），製造「一個一個停」的張力
const STRIP_LENGTHS = [72, 104, 138] // 三軸的滾動條長度；越長 → 高速期更明顯，整段轉動才有「轉轉轉」的感覺
const VEGAS_OUTSET = 12 // 機台外圍跑馬燈外擴距離

// 命中機率：拉霸不可能每拉必中。30% 命中、連續未中達閾值觸發保底
const WIN_PROBABILITY = 0.3
// 保底閾值隨機落在 [3, 5]，每次中獎後重新滾，讓玩家抓不到固定節奏
const PITY_THRESHOLD_MIN = 3
const PITY_THRESHOLD_MAX = 5

function _roll_pity_threshold(): number {
  const span = PITY_THRESHOLD_MAX - PITY_THRESHOLD_MIN + 1
  return PITY_THRESHOLD_MIN + Math.floor(Math.random() * span)
}

const store = use_funds_store()
const audio_store = use_audio_store()
const { stocks: pool, data_date: dataDate, loading, error } = storeToRefs(store)

interface ReelState {
  items: DrawableStock[]
  offset: number
  duration: number
  spinning: boolean
  settled: boolean
}

const reels = ref<ReelState[]>([
  { items: [], offset: 0, duration: 0, spinning: false, settled: false },
  { items: [], offset: 0, duration: 0, spinning: false, settled: false },
  { items: [], offset: 0, duration: 0, spinning: false, settled: false },
])

const result = ref<DrawableStock | null>(null)
const rolling = ref(false)
const jackpot = ref(false)
const miss = ref(false) // 上一次拉桿是「未中」
const miss_streak = ref(0) // 連續未中次數；達到 pity_threshold 強制命中
const pity_threshold = ref(_roll_pity_threshold()) // 本輪保底次數，命中後重新滾
const has_drawn = ref(false)

const etf_filter = ref<string[]>([...ETF_ORDER])
const is_dropdown_open = ref(false)
const dropdown_ref = ref<HTMLElement | null>(null)

// 機台容器測量（給跑馬燈用），與 LuckyDraw 的 vegas-lights 同一手法
const machine_ref = ref<HTMLElement | null>(null)
const vegas_dims = ref({ w: 0, h: 0 })
let _vegas_resize_obs: ResizeObserver | null = null

function _measure_vegas(): void {
  if (!machine_ref.value) return
  // 用 offsetWidth/offsetHeight 而非 getBoundingClientRect()。
  // 原因：JACKPOT 的 machine-slam 動畫會把 .machine 暫時 scale(1.05)，
  // getBoundingClientRect 會回傳「含 transform 後」的視覺尺寸，
  // 若 ResizeObserver 剛好在 scale 中觸發，vegas_dims 會被鎖死在放大值，
  // slam 動畫結束後跑馬燈就會比 frame 大一圈。
  // offsetWidth/offsetHeight 是 layout 原尺寸、不受 transform 影響。
  const el = machine_ref.value
  const w = el.offsetWidth
  const h = el.offsetHeight
  if (w <= 0 || h <= 0) return
  vegas_dims.value = {
    w: w + VEGAS_OUTSET * 2,
    h: h + VEGAS_OUTSET * 2,
  }
}

watch(machine_ref, (el) => {
  _vegas_resize_obs?.disconnect()
  _vegas_resize_obs = null
  if (el && typeof ResizeObserver !== 'undefined') {
    _measure_vegas()
    _vegas_resize_obs = new ResizeObserver(_measure_vegas)
    _vegas_resize_obs.observe(el)
  }
})

// ---- ETF 篩選 ----

const is_all_selected = computed({
  get: () => etf_filter.value.length === ETF_ORDER.length,
  set: (val: boolean) => {
    etf_filter.value = val ? [...ETF_ORDER] : []
  },
})

const filtered_pool = computed(() => {
  if (etf_filter.value.length === 0) return []
  return pool.value.filter((stock) =>
    stock.sources.some((x) => etf_filter.value.includes(x.etf_code)),
  )
})

const grouped_sources = computed(() => {
  if (!result.value) return { selected: [], unselected: [] }
  const selected: typeof result.value.sources = []
  const unselected: typeof result.value.sources = []
  const sorted = [...result.value.sources].sort(
    (a, b) =>
      ETF_ORDER.indexOf(a.etf_code as (typeof ETF_ORDER)[number]) -
      ETF_ORDER.indexOf(b.etf_code as (typeof ETF_ORDER)[number]),
  )
  for (const src of sorted) {
    if (etf_filter.value.includes(src.etf_code)) selected.push(src)
    else unselected.push(src)
  }
  return { selected, unselected }
})

// ---- 動效相關 ----

// 曲線：(0.05, 0.55, 0.65, 1) → 起步即接近最高速、長時間維持高速、收尾才滑順減速；
// 比原本的 (0.12, 0.65, 0.2, 1) 更像真實拉霸機的「持續轉、最後才慢」感
const reel_styles = computed(() =>
  reels.value.map((r) => ({
    transform: `translateY(${r.offset}px)`,
    transition:
      r.duration > 0
        ? `transform ${r.duration}ms cubic-bezier(0.05, 0.55, 0.65, 1)`
        : 'none',
  })),
)

interface ConfettiPiece {
  id: number
  left: number
  delay: number
  duration: number
  color: string
  size: number
}

interface CoinPiece {
  id: number
  left: number
  delay: number
  duration: number
  drift: number
}

const confetti_pieces = ref<ConfettiPiece[]>([])
const coin_pieces = ref<CoinPiece[]>([])

const CONFETTI_COLORS = ['#ffd166', '#ff7ac8', '#7ec8ff', '#b3b8ff', '#a3ffaf', '#ff9b6a']

function _spawn_celebration(): void {
  confetti_pieces.value = Array.from({ length: 42 }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    delay: Math.random() * 0.5,
    duration: 1.6 + Math.random() * 1.4,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length]!,
    size: 6 + Math.random() * 8,
  }))
  coin_pieces.value = Array.from({ length: 16 }, (_, i) => ({
    id: i,
    left: 6 + Math.random() * 88,
    delay: Math.random() * 0.4,
    duration: 1.4 + Math.random() * 0.9,
    drift: (Math.random() - 0.5) * 60,
  }))
}

function prefers_reduced_motion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
  )
}

function buzz(pattern: number[]): void {
  if (prefers_reduced_motion()) return
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    try {
      navigator.vibrate?.(pattern)
    } catch {
      // ignore
    }
  }
}

function handle_click_outside(event: MouseEvent): void {
  if (
    is_dropdown_open.value &&
    dropdown_ref.value &&
    !dropdown_ref.value.contains(event.target as Node)
  ) {
    is_dropdown_open.value = false
  }
}

// 安全網：使用者切換篩選時，若 rolling 仍意外卡住，視為「想中斷」的訊號，
// 強制把三軸 / rolling / tick timer 歸位，避免按鈕永久 disabled。
watch(etf_filter, () => {
  if (!rolling.value) return
  _stop_ticks()
  rolling.value = false
  miss.value = false
  for (const reel of reels.value) {
    reel.spinning = false
    reel.settled = false
  }
})

onMounted(() => {
  store.ensure_loaded()
  document.addEventListener('mousedown', handle_click_outside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handle_click_outside)
  _vegas_resize_obs?.disconnect()
  _vegas_resize_obs = null
  _stop_ticks()
})

// ---- 滾動條建構 ----

function _build_strip(
  src_pool: DrawableStock[],
  final: DrawableStock,
  count: number,
): DrawableStock[] {
  // 最後一格 = 最終結果，倒數第二格才是「停在中線」的那一格
  // 視窗會顯示三格：上 / 中(=中獎) / 下
  // 所以排版：[...random*(count-3), winner_above, FINAL_CENTER, winner_below]
  const strip: DrawableStock[] = []
  for (let i = 0; i < count - 3; i++) {
    const idx = Math.floor(Math.random() * src_pool.length)
    strip.push(src_pool[idx]!)
  }
  // 上下兩個 padding 也隨機，避免在中線旁邊就先「劇透」
  strip.push(_random_other(src_pool, final))
  strip.push(final)
  strip.push(_random_other(src_pool, final))
  return strip
}

function _random_other(src_pool: DrawableStock[], avoid: DrawableStock): DrawableStock {
  if (src_pool.length <= 1) return src_pool[0]!
  for (let tries = 0; tries < 8; tries++) {
    const idx = Math.floor(Math.random() * src_pool.length)
    if (src_pool[idx]!.name !== avoid.name) return src_pool[idx]!
  }
  return src_pool[0]!
}

function _final_offset(strip_len: number): number {
  // FINAL 在 index = strip_len - 2，欲讓它出現在 3 格視窗的中列，
  // 視窗中列對應 strip index = strip_len - 2 → offset = -(strip_len - 2 - 1) * H
  return -(strip_len - 3) * ITEM_HEIGHT
}

/**
 * 三軸都不同（或至少不全相同）的「未中」組合。
 * 容許 2 of a kind（兩軸相同）製造「啊—就差一個」的緊張感。
 */
function _pick_loss_combo(src_pool: DrawableStock[]): DrawableStock[] {
  if (src_pool.length < 2) {
    // 池子只有 1 檔時無法製造未中；直接全部一樣（仍會走 jackpot 流程）
    const s = src_pool[0]!
    return [s, s, s]
  }
  for (let tries = 0; tries < 12; tries++) {
    const a = pick_random_stock(src_pool)
    const b = pick_random_stock(src_pool)
    const c = pick_random_stock(src_pool)
    if (!(a.name === b.name && b.name === c.name)) {
      return [a, b, c]
    }
  }
  // 極端情況保底：強制讓最後一軸不同
  const a = pick_random_stock(src_pool)
  let c = pick_random_stock(src_pool)
  for (let t = 0; t < 8 && c.name === a.name; t++) c = pick_random_stock(src_pool)
  return [a, a, c]
}

// ---- 未中的低音 buzz（Web Audio API 直接合成，免額外資源） ----

let _local_audio_ctx: AudioContext | null = null

function _ensure_audio_ctx(): AudioContext | null {
  if (typeof window === 'undefined') return null
  try {
    const Ctor =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext
    if (!Ctor) return null
    _local_audio_ctx ??= new Ctor()
    return _local_audio_ctx
  } catch {
    return null
  }
}

function _play_miss(): void {
  if (prefers_reduced_motion()) return
  const ctx = _ensure_audio_ctx()
  if (!ctx) return
  try {
    const now = ctx.currentTime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sawtooth'
    osc.frequency.setValueAtTime(260, now)
    osc.frequency.exponentialRampToValueAtTime(80, now + 0.42)
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.16, now + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.5)
    osc.connect(gain).connect(ctx.destination)
    osc.start(now)
    osc.stop(now + 0.55)
  } catch {
    // ignore
  }
}

// ---- 滾動聲效 ----

let _tick_timer: number | null = null

function _start_ticks(): void {
  _stop_ticks()
  function tick(): void {
    if (!rolling.value) return
    audio_store.play_tick()
    _tick_timer = window.setTimeout(tick, 78)
  }
  tick()
}

function _stop_ticks(): void {
  if (_tick_timer !== null) {
    window.clearTimeout(_tick_timer)
    _tick_timer = null
  }
}

function _delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

// ---- 主流程：拉桿 ----

async function pull_lever(): Promise<void> {
  if (rolling.value || filtered_pool.value.length === 0) return
  rolling.value = true
  jackpot.value = false
  miss.value = false
  result.value = null
  is_dropdown_open.value = false
  confetti_pieces.value = []
  coin_pieces.value = []

  // 命中判定：30% 機率；連續未中達本輪保底次數（3~5 隨機）強制命中
  const force_win = miss_streak.value >= pity_threshold.value
  const is_win = force_win || Math.random() < WIN_PROBABILITY

  try {
    // 三軸各自的落點：win → 三軸都是同一檔；miss → 至少兩軸不同
    // 在 try 內部讀取 filtered_pool，使用者切換篩選時若 pool 變空，這裡會 throw 並走 finally 重置
    const pool_snapshot = [...filtered_pool.value]
    if (pool_snapshot.length === 0) throw new Error('篩選後成分股池為空')

    const finals: DrawableStock[] = is_win
      ? (() => {
          const w = pick_random_stock(pool_snapshot)
          return [w, w, w]
        })()
      : _pick_loss_combo(pool_snapshot)

    // 步驟 1：重置三軸到 offset=0、無 transition，並換上新滾動條
    for (let i = 0; i < 3; i++) {
      const reel = reels.value[i]!
      reel.items = _build_strip(pool_snapshot, finals[i]!, STRIP_LENGTHS[i]!)
      reel.offset = 0
      reel.duration = 0
      reel.spinning = false
      reel.settled = false
    }

    // 步驟 2：等 Vue commit + 一幀，確保「無 transition 的 offset=0」先生效
    await nextTick()
    await new Promise<void>((r) =>
      requestAnimationFrame(() => requestAnimationFrame(() => r())),
    )

    // 步驟 3：套上 transition + 終點 offset，三軸同時起跑
    for (let i = 0; i < 3; i++) {
      const reel = reels.value[i]!
      reel.duration = REEL_DURATIONS[i]!
      reel.offset = _final_offset(STRIP_LENGTHS[i]!)
      reel.spinning = true
    }

    _start_ticks()
    buzz([20, 30, 20, 30, 20])

    // 步驟 4：依序等三軸落定，每停一軸響一聲「鐺」
    const gaps = [
      REEL_DURATIONS[0]!,
      REEL_DURATIONS[1]! - REEL_DURATIONS[0]!,
      REEL_DURATIONS[2]! - REEL_DURATIONS[1]!,
    ]
    for (let i = 0; i < 3; i++) {
      await _delay(gaps[i]!)
      const reel = reels.value[i]!
      reel.spinning = false
      reel.settled = true
      audio_store.play_ding()
      buzz([60])
    }

    has_drawn.value = true

    if (is_win) {
      // 命中：JACKPOT 全套特效
      result.value = finals[0]!
      miss_streak.value = 0
      pity_threshold.value = _roll_pity_threshold() // 下一輪保底重新滾，玩家抓不到固定節奏
      jackpot.value = true
      _spawn_celebration()
      buzz([120, 40, 90, 40, 70])
      window.setTimeout(() => audio_store.play_ding(), 140)
      window.setTimeout(() => audio_store.play_ding(), 300)
      window.setTimeout(() => audio_store.play_ding(), 480)
      window.setTimeout(() => {
        jackpot.value = false
      }, 2600)
    } else {
      // 未中：低音 buzz + 顯示「再拉一次」提示
      miss.value = true
      miss_streak.value += 1
      _play_miss()
      buzz([40, 60, 40])
    }
  } catch (err) {
    // 防呆：任何階段拋例外都要把三軸 / rolling / tick timer 歸位
    // 否則按鈕會永久 disabled，使用者就完全卡死
    console.error('[SlotMachine] pull_lever 異常：', err)
    for (const reel of reels.value) {
      reel.spinning = false
      reel.settled = false
    }
  } finally {
    _stop_ticks()
    rolling.value = false
  }
}
</script>

<template>
  <main class="page" :class="{ 'is-rolling': rolling, 'is-jackpot': jackpot }">
    <div class="aurora" aria-hidden="true"></div>
    <div v-if="jackpot" class="page-flash" aria-hidden="true"></div>

    <header class="hero">
      <span class="eyebrow">DestinyOrder · 命定拉霸機</span>
      <h1>台股 ETF 拉霸機</h1>
      <!-- 副標題文字已移除但保留佔位行：兩個 &nbsp; + 手機版 br，使桌面 1 行、手機 2 行，
           與原本副標的高度節奏一致，避免視覺重心上移 -->
      <p class="subtitle" aria-hidden="true">&nbsp;<br class="br-mobile-only" />&nbsp;</p>
    </header>

    <section class="stage">
      <div v-if="loading && pool.length === 0" class="state state-loading">
        <div class="spinner" />
        <p>載入最新基金成分股…</p>
      </div>

      <div v-else-if="error" class="state state-error">
        <p>⚠️ {{ error }}</p>
        <p class="hint">請確認後端資料夾 backend/data/funds 存在且包含最新日期。</p>
      </div>

      <template v-else>
        <div class="machine" :class="{ 'is-rolling': rolling, 'is-jackpot': jackpot, 'is-miss': miss && !rolling }">
          <!-- 賭城跑馬燈：環繞整台機器外緣 -->
          <div
            v-show="vegas_dims.w > 0"
            class="vegas-lights"
            :style="{ width: vegas_dims.w + 'px', height: vegas_dims.h + 'px' }"
            aria-hidden="true"
          >
            <svg
              class="vegas-svg"
              :width="vegas_dims.w"
              :height="vegas_dims.h"
              :viewBox="`0 0 ${vegas_dims.w} ${vegas_dims.h}`"
              preserveAspectRatio="none"
            >
              <rect
                class="vegas-rim vegas-rim-gold"
                x="3"
                y="3"
                :width="Math.max(0, vegas_dims.w - 6)"
                :height="Math.max(0, vegas_dims.h - 6)"
                rx="26"
                ry="26"
                vector-effect="non-scaling-stroke"
              />
              <rect
                class="vegas-rim vegas-rim-pink"
                x="3"
                y="3"
                :width="Math.max(0, vegas_dims.w - 6)"
                :height="Math.max(0, vegas_dims.h - 6)"
                rx="26"
                ry="26"
                vector-effect="non-scaling-stroke"
              />
            </svg>
          </div>

          <div ref="machine_ref" class="machine-frame">
            <!-- 頂部一列：命運三連（靠左）｜ JACKPOT 招牌（置中）｜ 篩選下拉（靠右） -->
            <div class="machine-header">
              <span class="card-label">命運三連</span>
              <div class="machine-sign" :class="{ 'is-jackpot': jackpot }">
                <span class="sign-star">★</span>
                <span class="sign-text">JACKPOT</span>
                <span class="sign-star">★</span>
              </div>
              <span ref="dropdown_ref" class="dropdown-container">
                <button
                  type="button"
                  class="dropdown-toggle"
                  :aria-expanded="is_dropdown_open"
                  @click="is_dropdown_open = !is_dropdown_open"
                >
                  <!--
                    「全部」狀態僅在行動裝置（≤540px）強制換行成兩行，避免窄欄時
                    「篩選：全」+「部」這種斷字；桌面寬度仍維持單行。
                    其他狀態（已選 N 檔）字串較短，維持單行。
                  -->
                  <template v-if="etf_filter.length === ETF_ORDER.length">
                    篩選：<br class="br-mobile-only" />全部
                  </template>
                  <template v-else>
                    篩選 {{ etf_filter.length }} 檔
                  </template>
                  <span class="arrow" :class="{ open: is_dropdown_open }">▼</span>
                </button>
                <div v-show="is_dropdown_open" class="dropdown-menu">
                  <label class="dropdown-item">
                    <input v-model="is_all_selected" type="checkbox" />
                    全部
                  </label>
                  <label v-for="code in ETF_ORDER" :key="code" class="dropdown-item">
                    <input v-model="etf_filter" type="checkbox" :value="code" />
                    {{ code }}
                  </label>
                </div>
              </span>
            </div>

            <!-- 三軸區 -->
            <div class="reels-area">
              <div class="win-line" :class="{ 'is-active': result && !rolling }" aria-hidden="true">
                <span class="win-arrow win-arrow-left">▶</span>
                <span class="win-arrow win-arrow-right">◀</span>
              </div>
              <div class="reels">
                <div
                  v-for="(reel, i) in reels"
                  :key="i"
                  class="reel"
                  :class="{
                    'is-spinning': reel.spinning,
                    'is-settled': reel.settled,
                    'is-jackpot': jackpot,
                  }"
                >
                  <div class="reel-window">
                    <div class="reel-strip" :style="reel_styles[i]">
                      <div
                        v-for="(item, idx) in reel.items"
                        :key="idx"
                        class="reel-item"
                      >
                        <div class="reel-symbol">{{ item.symbol ?? '——' }}</div>
                        <div class="reel-name">{{ item.name }}</div>
                      </div>
                    </div>
                    <div class="reel-fade reel-fade-top" aria-hidden="true" />
                    <div class="reel-fade reel-fade-bottom" aria-hidden="true" />
                    <div
                      class="reel-pay-glow"
                      :class="{ active: reel.settled && !!result }"
                      aria-hidden="true"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- 命中明細：產業 + ETF pills；未中時改顯示挑釁文案 -->
            <div
              class="result-area"
              :class="{
                'has-result': result && !rolling,
                'is-miss': miss && !rolling,
              }"
            >
              <template v-if="result && !rolling">
                <div class="result-meta">
                  <span class="meta-item">
                    <span class="meta-key">產業別</span>
                    <span class="meta-val">{{ result.industry ?? '未分類' }}</span>
                  </span>
                </div>
                <div class="result-sources">
                  <span
                    v-for="src in grouped_sources.selected"
                    :key="src.etf_code"
                    class="pill"
                    :title="`${src.etf_name} · 權重 ${src.weight}`"
                  >
                    <span class="pill-code">{{ src.etf_code }}</span>
                    <span class="pill-weight">{{ src.weight }}</span>
                  </span>
                  <template v-if="grouped_sources.unselected.length > 0">
                    <span class="source-divider">|</span>
                    <span class="source-hint">其他收錄</span>
                    <span
                      v-for="src in grouped_sources.unselected"
                      :key="src.etf_code"
                      class="pill pill-ghost"
                      :title="`${src.etf_name} · 權重 ${src.weight}`"
                    >
                      <span class="pill-code">{{ src.etf_code }}</span>
                      <span class="pill-weight">{{ src.weight }}</span>
                    </span>
                  </template>
                </div>
              </template>
              <div v-else-if="miss && !rolling" class="result-miss">
                <span class="miss-icon" aria-hidden="true">✘</span>
                <span class="miss-text">三軸未對齊 · 命運還沒選定</span>
                <span v-if="miss_streak >= 3" class="miss-hint">
                  已連續 {{ miss_streak }} 次未中 — 再拉一次！
                </span>
                <span v-else class="miss-hint">再拉一次試試手氣</span>
              </div>
              <div v-else class="result-placeholder">
                {{ rolling ? '命運轉動中！' : '— 等待命運降臨 —' }}
              </div>
            </div>

            <!-- 拉桿按鈕 -->
            <div class="lever-row">
              <button
                type="button"
                class="lever-btn"
                :class="{ 'is-pulled': rolling }"
                :disabled="rolling || filtered_pool.length === 0"
                @click="pull_lever"
              >
                <span class="lever-knob" aria-hidden="true">
                  <span class="lever-knob-shine" />
                </span>
                <span class="lever-text">
                  {{
                    rolling
                      ? '滾動中…'
                      : miss
                        ? '不甘心，再拉！'
                        : has_drawn
                          ? '再拉一次'
                          : '拉動拉桿'
                  }}
                </span>
              </button>
            </div>
          </div>

          <!-- JACKPOT 飛字 -->
          <Transition name="jackpot-text">
            <div v-if="jackpot" class="jackpot-banner" aria-hidden="true">
              <span class="jackpot-banner-text">命定！</span>
            </div>
          </Transition>

          <!-- 彩帶 -->
          <div v-if="jackpot" class="confetti" aria-hidden="true">
            <i
              v-for="p in confetti_pieces"
              :key="p.id"
              class="confetti-piece"
              :style="{
                left: p.left + '%',
                width: p.size + 'px',
                height: p.size * 1.6 + 'px',
                background: p.color,
                animationDelay: p.delay + 's',
                animationDuration: p.duration + 's',
              }"
            />
          </div>

          <!-- 金幣雨 -->
          <div v-if="jackpot" class="coins" aria-hidden="true">
            <i
              v-for="c in coin_pieces"
              :key="c.id"
              class="coin-piece"
              :style="{
                left: c.left + '%',
                animationDelay: c.delay + 's',
                animationDuration: c.duration + 's',
                '--drift': c.drift + 'px',
              }"
            />
          </div>
        </div>

        <p class="disclaimer">
          ※ 本工具僅供研究參考，不構成任何投資建議；實際投資決策請審慎評估。<br class="disclaimer-break" /><template
            v-if="dataDate"
            >資料抓取日期 {{ dataDate }}（各 ETF 實際公告時間不同）。</template
          >
        </p>
      </template>
    </section>
  </main>
</template>

<style scoped>
.page {
  position: relative;
  /* 鎖定為視窗高度，整頁不出現 scrollbar；超短螢幕由 @media (max-height) 釋放 */
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  padding: clamp(0.8rem, 2.2vw, 1.8rem) clamp(1rem, 4vw, 3rem)
    calc(var(--app-footer-height) + clamp(0.3rem, 1vw, 0.7rem));
  color: #e8eaf6;
  font-family:
    'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif;
  background:
    radial-gradient(1200px 600px at 10% -20%, #2a1f6b 0%, transparent 60%),
    radial-gradient(900px 500px at 110% 10%, #1e4778 0%, transparent 55%),
    linear-gradient(180deg, #0b0f24 0%, #070a1a 100%);
  display: flex;
  flex-direction: column;
  gap: clamp(0.3rem, 0.8vw, 0.6rem);
}

.aurora {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 0%, rgba(124, 92, 255, 0.18), transparent 50%),
    radial-gradient(circle at 80% 90%, rgba(83, 196, 255, 0.12), transparent 50%);
  pointer-events: none;
  transition: filter 0.3s ease;
}
.page.is-rolling .aurora {
  animation: aurora-rage 0.55s ease-in-out infinite alternate;
  filter: saturate(1.4) brightness(1.3);
}
@keyframes aurora-rage {
  from { transform: scale(1); opacity: 0.85; }
  to { transform: scale(1.06); opacity: 1.2; }
}
.page.is-jackpot { animation: page-quake 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97); }
@keyframes page-quake {
  0% { transform: translate3d(0,0,0); }
  15% { transform: translate3d(-5px, 2px, 0); }
  30% { transform: translate3d(6px, -3px, 0); }
  45% { transform: translate3d(-6px, 3px, 0); }
  60% { transform: translate3d(4px, -2px, 0); }
  75% { transform: translate3d(-2px, 1px, 0); }
  100% { transform: translate3d(0,0,0); }
}

.page-flash {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(
      circle at 50% 50%,
      rgba(255, 209, 102, 0.55) 0%,
      rgba(255, 122, 200, 0.25) 35%,
      transparent 70%
    );
  pointer-events: none;
  z-index: 9999;
  animation: page-flash 0.5s ease-out forwards;
  mix-blend-mode: screen;
}
@keyframes page-flash {
  0% { opacity: 0.95; }
  40% { opacity: 0.5; }
  100% { opacity: 0; }
}

/* ---------- Hero ---------- */

.hero {
  position: relative;
  max-width: 720px;
  margin: 0 auto;
  text-align: center;
  flex-shrink: 0;
}
.eyebrow {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  font-size: clamp(0.66rem, 2vw, 0.74rem);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  border-radius: 999px;
  border: 1px solid rgba(255, 209, 102, 0.32);
  background: rgba(255, 209, 102, 0.08);
  color: #ffd9a0;
}
.hero h1 {
  margin: 0.4rem 0 0.25rem;
  font-size: clamp(1.55rem, 4.8vw, 2.4rem);
  font-weight: 800;
  letter-spacing: 0.02em;
  background: linear-gradient(90deg, #fff 0%, #ffd166 50%, #ff7ac8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  line-height: 1.15;
}
.subtitle {
  margin: 0 auto;
  max-width: 540px;
  color: #b1b6d6;
  font-size: clamp(0.78rem, 2.2vw, 0.86rem);
  line-height: 1.55;
}

/* ---------- Stage / Machine ---------- */

.stage {
  position: relative;
  max-width: 580px;
  width: 100%;
  margin: 0 auto;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  /* 機台貼近 hero、disclaimer 由 margin-top: auto 推到底 */
  justify-content: flex-start;
  align-items: stretch;
  gap: clamp(0.4rem, 1vw, 0.7rem);
}

.state { text-align: center; padding: clamp(2rem, 8vw, 3rem) 1rem; color: #b1b6d6; }
.state-error p:first-child { color: #ff9a9a; font-weight: 600; }
.hint { margin-top: 0.4rem; font-size: 0.85rem; color: #8a8fae; }
.spinner {
  width: 32px; height: 32px;
  margin: 0 auto 0.8rem;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.12);
  border-top-color: #ffd166;
  animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.machine {
  position: relative;
  /* 機台本體置中、外圈跑馬燈可以絕對定位於 -outset */
}

/* 跑馬燈：金 + 粉雙層，金色順時針、粉色逆時針，交織出霓虹感 */
.vegas-lights {
  position: absolute;
  top: -12px;
  left: -12px;
  pointer-events: none;
  z-index: 4;
  animation: vegas-pulse 0.7s ease-in-out infinite alternate;
}
.vegas-svg { display: block; overflow: visible; }
.vegas-rim { fill: none; stroke-linecap: round; stroke-dasharray: 10 12; }
.vegas-rim-gold {
  stroke: #ffd166;
  stroke-width: 4;
  animation: vegas-chase-cw 4s linear infinite;
  filter:
    drop-shadow(0 0 5px #ffd166)
    drop-shadow(0 0 12px rgba(255, 209, 102, 0.55));
}
.vegas-rim-pink {
  stroke: #ff7ac8;
  stroke-width: 2;
  stroke-dasharray: 4 18;
  animation: vegas-chase-ccw 3s linear infinite;
  filter:
    drop-shadow(0 0 4px #ff7ac8)
    drop-shadow(0 0 10px rgba(255, 122, 200, 0.55));
  opacity: 0.85;
}
.machine.is-rolling .vegas-rim-gold { animation-duration: 1s; stroke-width: 5; }
.machine.is-rolling .vegas-rim-pink { animation-duration: 0.75s; }
.machine.is-jackpot .vegas-rim-gold { animation-duration: 0.55s; filter: drop-shadow(0 0 12px #ffd166) drop-shadow(0 0 22px #ffd166); }
.machine.is-jackpot .vegas-rim-pink { animation-duration: 0.4s; }

@keyframes vegas-chase-cw { to { stroke-dashoffset: -880; } }
@keyframes vegas-chase-ccw { to { stroke-dashoffset: 880; } }
@keyframes vegas-pulse {
  from { filter: brightness(0.95) saturate(1); }
  to { filter: brightness(1.3) saturate(1.45); }
}

/* 機體本身 */
.machine-frame {
  position: relative;
  z-index: 1;
  padding: clamp(0.6rem, 1.8vw, 0.95rem) clamp(0.9rem, 3vw, 1.4rem)
    clamp(0.6rem, 1.8vw, 0.95rem);
  border-radius: clamp(18px, 3.5vw, 24px);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%),
    radial-gradient(120% 80% at 50% 0%, rgba(255, 209, 102, 0.08) 0%, transparent 65%);
  border: 1px solid rgba(255, 209, 102, 0.22);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow:
    0 30px 60px -30px rgba(0, 0, 0, 0.7),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: clamp(0.45rem, 1.2vw, 0.75rem);
  transition: box-shadow 0.4s ease, transform 0.4s ease;
}
.machine.is-miss .machine-frame {
  animation: machine-shake 0.55s cubic-bezier(0.36, 0.07, 0.19, 0.97);
  border-color: rgba(255, 122, 122, 0.45);
  box-shadow:
    0 30px 60px -30px rgba(0, 0, 0, 0.7),
    0 0 0 1px rgba(255, 122, 122, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
@keyframes machine-shake {
  0% { transform: translate3d(0, 0, 0); }
  20% { transform: translate3d(-3px, 0, 0); }
  40% { transform: translate3d(3px, 0, 0); }
  60% { transform: translate3d(-2px, 0, 0); }
  80% { transform: translate3d(2px, 0, 0); }
  100% { transform: translate3d(0, 0, 0); }
}
/* 將 slam 動畫套在 .machine（vegas-lights 與 frame 的共同父層），
   兩者才會一起 scale，跑馬燈邊界才不會在 JACKPOT 時跟 frame 錯開。 */
.machine.is-jackpot {
  animation: machine-slam 0.7s cubic-bezier(0.22, 1.5, 0.32, 1) forwards;
  transform-origin: center center;
}
.machine.is-jackpot .machine-frame {
  box-shadow:
    0 50px 90px -20px rgba(255, 209, 102, 0.55),
    0 0 0 2px rgba(255, 209, 102, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
@keyframes machine-slam {
  0% { transform: scale(1.05) translateY(-4px); }
  40% { transform: scale(0.97) translateY(4px); }
  70% { transform: scale(1.02) translateY(-1px); }
  100% { transform: scale(1) translateY(0); }
}

/* ---------- 頂部招牌 ---------- */

.machine-sign {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(255, 209, 102, 0.18) 0%, rgba(255, 122, 200, 0.12) 100%);
  border: 1px solid rgba(255, 209, 102, 0.35);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.18),
    0 0 18px rgba(255, 209, 102, 0.2);
  font-size: clamp(0.72rem, 2.2vw, 0.82rem);
  font-weight: 800;
  letter-spacing: 0.3em;
  color: #ffe7a3;
  text-shadow: 0 0 12px rgba(255, 209, 102, 0.55);
  align-self: center;
}
.sign-text {
  background: linear-gradient(180deg, #fff5d6 0%, #ffb84a 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}
.sign-star {
  display: inline-block;
  color: #ffd166;
  animation: sign-twinkle 1.4s ease-in-out infinite alternate;
  filter: drop-shadow(0 0 6px rgba(255, 209, 102, 0.8));
}
.sign-star:last-child { animation-delay: -0.7s; }
@keyframes sign-twinkle {
  from { transform: scale(1) rotate(-8deg); opacity: 0.8; }
  to { transform: scale(1.18) rotate(8deg); opacity: 1; }
}
.machine-sign.is-jackpot {
  animation: sign-jackpot 0.4s ease-in-out infinite alternate;
}
@keyframes sign-jackpot {
  from {
    background: linear-gradient(180deg, rgba(255, 209, 102, 0.35), rgba(255, 122, 200, 0.25));
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.25), 0 0 26px rgba(255, 209, 102, 0.7);
  }
  to {
    background: linear-gradient(180deg, rgba(255, 122, 200, 0.4), rgba(255, 209, 102, 0.3));
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.3), 0 0 38px rgba(255, 122, 200, 0.7);
  }
}

/* ---------- 篩選列 ---------- */

.machine-header {
  position: relative;
  z-index: 10;
  display: grid;
  /* 三欄：左 1fr 命運三連、中 auto JACKPOT 招牌、右 1fr 篩選下拉 */
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 0.5rem;
}
.card-label {
  justify-self: start;
  font-size: clamp(0.7rem, 2.4vw, 0.75rem);
  letter-spacing: 0.22em;
  color: #8a8fae;
  text-transform: uppercase;
}
.machine-header .dropdown-container {
  justify-self: end;
}

.dropdown-container { position: relative; display: inline-block; }
.dropdown-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: transparent;
  border: none;
  color: #c9cce8;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  cursor: pointer;
  font-family: inherit;
  font-size: clamp(0.7rem, 2.4vw, 0.75rem);
  font-weight: 500;
  letter-spacing: 0.05em;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}
.dropdown-toggle:hover { color: #ffd9a0; background: rgba(255, 209, 102, 0.08); }
.arrow { font-size: 0.6rem; transition: transform 0.2s ease; }
.arrow.open { transform: rotate(180deg); }
.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.4rem);
  right: 0;
  background: rgba(11, 15, 36, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 209, 102, 0.3);
  border-radius: 10px;
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  z-index: 100;
  min-width: 140px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  text-align: left;
}
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.85rem;
  color: #e8eaf6;
  cursor: pointer;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  transition: background 0.2s ease;
  user-select: none;
}
.dropdown-item:hover { background: rgba(255, 255, 255, 0.08); }
.dropdown-item input[type='checkbox'] {
  appearance: none;
  background-color: rgba(255, 255, 255, 0.1);
  margin: 0;
  font: inherit;
  color: currentColor;
  width: 1.15em;
  height: 1.15em;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.15em;
  display: grid;
  place-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.dropdown-item input[type='checkbox']::before {
  content: '';
  width: 0.65em;
  height: 0.65em;
  transform: scale(0);
  transition: 120ms transform ease-in-out;
  box-shadow: inset 1em 1em #fff;
  background-color: CanvasText;
  transform-origin: center;
  clip-path: polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 43% 62%);
}
.dropdown-item input[type='checkbox']:checked {
  background-color: #ffd166;
  border-color: #ffd166;
}
.dropdown-item input[type='checkbox']:checked::before { transform: scale(1); }

/* ---------- 三軸區 ---------- */

.reels-area {
  position: relative;
  padding: 0.45rem;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(0, 0, 0, 0.4) 0%, rgba(0, 0, 0, 0.55) 100%);
  border: 1px solid rgba(255, 209, 102, 0.2);
  box-shadow:
    inset 0 4px 14px rgba(0, 0, 0, 0.6),
    0 0 0 1px rgba(0, 0, 0, 0.4);
}

.win-line {
  position: absolute;
  left: 0.45rem;
  right: 0.45rem;
  top: 50%;
  height: 0;
  z-index: 6;
  pointer-events: none;
  border-top: 2px dashed rgba(255, 209, 102, 0.55);
  transform: translateY(-1px);
  box-shadow: 0 0 14px rgba(255, 209, 102, 0.5);
  transition: border-color 0.4s ease, box-shadow 0.4s ease;
}
.win-line.is-active {
  border-top-color: #ffd166;
  border-top-style: solid;
  box-shadow: 0 0 22px #ffd166, 0 0 38px rgba(255, 209, 102, 0.6);
  animation: win-line-pulse 0.9s ease-in-out infinite alternate;
}
@keyframes win-line-pulse {
  from { box-shadow: 0 0 18px rgba(255, 209, 102, 0.6); }
  to { box-shadow: 0 0 36px #ffd166, 0 0 60px rgba(255, 122, 200, 0.5); }
}
.win-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.9rem;
  color: #ffd166;
  text-shadow: 0 0 8px #ffd166;
}
.win-arrow-left { left: -0.6rem; }
.win-arrow-right { right: -0.6rem; }

.reels {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.45rem;
}

.reel {
  position: relative;
}
.reel-window {
  position: relative;
  height: calc(88px * 3); /* 顯示 3 列；高度需與 JS 的 ITEM_HEIGHT 同步 */
  overflow: hidden;
  border-radius: 10px;
  background:
    linear-gradient(180deg, #050714 0%, #0d122b 50%, #050714 100%);
  border: 1px solid rgba(255, 209, 102, 0.28);
  box-shadow:
    inset 0 2px 10px rgba(0, 0, 0, 0.7),
    inset 0 -2px 6px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(0, 0, 0, 0.6);
}
.reel.is-spinning .reel-window {
  border-color: rgba(255, 209, 102, 0.5);
  box-shadow:
    inset 0 2px 10px rgba(0, 0, 0, 0.7),
    0 0 14px rgba(255, 209, 102, 0.3);
}
.reel.is-settled .reel-window {
  border-color: #ffd166;
  box-shadow:
    inset 0 2px 10px rgba(0, 0, 0, 0.7),
    0 0 18px rgba(255, 209, 102, 0.55);
}
.reel.is-jackpot .reel-window {
  animation: reel-jackpot 0.32s ease-in-out infinite alternate;
}
@keyframes reel-jackpot {
  from { box-shadow: inset 0 2px 10px rgba(0,0,0,0.7), 0 0 14px #ffd166; }
  to { box-shadow: inset 0 2px 10px rgba(0,0,0,0.7), 0 0 28px #ffd166, 0 0 44px rgba(255, 122, 200, 0.55); }
}

.reel-strip {
  position: absolute;
  inset: 0;
  /* transform / transition 由 inline style 控制 */
  will-change: transform;
}
/* 滾動中加上垂直方向的動態模糊與略略飽和度提升，營造高速感 */
.reel.is-spinning .reel-strip {
  filter: blur(0.6px) saturate(1.15);
  animation: reel-shake-y 0.06s linear infinite;
}
@keyframes reel-shake-y {
  0%, 100% { margin-top: 0; }
  50% { margin-top: 0.5px; }
}
.reel-item {
  height: 88px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  padding: 0.4rem 0.5rem;
  text-align: center;
}
.reel-symbol {
  font-size: clamp(1.25rem, 4.4vw, 1.65rem);
  font-weight: 800;
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
  background: linear-gradient(180deg, #fff5d6 0%, #ffd166 70%, #ff9b3c 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 12px rgba(255, 209, 102, 0.3);
  line-height: 1.1;
}
.reel-name {
  font-size: clamp(0.66rem, 1.9vw, 0.72rem);
  color: #d8dbf3;
  font-weight: 500;
  letter-spacing: 0.02em;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

/* 視窗上下漸層淡出（強化「卷軸」感） */
.reel-fade {
  position: absolute;
  left: 0; right: 0;
  height: 36%;
  pointer-events: none;
  z-index: 2;
}
.reel-fade-top {
  top: 0;
  background: linear-gradient(180deg, rgba(5, 7, 20, 0.95) 0%, rgba(5, 7, 20, 0) 100%);
}
.reel-fade-bottom {
  bottom: 0;
  background: linear-gradient(0deg, rgba(5, 7, 20, 0.95) 0%, rgba(5, 7, 20, 0) 100%);
}

/* 中線高亮：停定後讓中央列發光 */
.reel-pay-glow {
  position: absolute;
  left: 0; right: 0;
  top: 50%;
  height: 33.33%;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 3;
  background:
    linear-gradient(90deg, transparent 0%, rgba(255, 209, 102, 0.18) 50%, transparent 100%);
  border-top: 1px solid transparent;
  border-bottom: 1px solid transparent;
  opacity: 0;
  transition: opacity 0.4s ease;
}
.reel-pay-glow.active {
  opacity: 1;
  border-top-color: rgba(255, 209, 102, 0.45);
  border-bottom-color: rgba(255, 209, 102, 0.45);
  animation: pay-pulse 1.2s ease-in-out infinite alternate;
}
@keyframes pay-pulse {
  from { background: linear-gradient(90deg, transparent, rgba(255, 209, 102, 0.18), transparent); }
  to { background: linear-gradient(90deg, transparent, rgba(255, 209, 102, 0.42), transparent); }
}

/* ---------- 命中明細 ---------- */

.result-area {
  position: relative;
  min-height: 52px;
  padding: 0.5rem 0.8rem;
  border-radius: 12px;
  border: 1px dashed rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  transition: border-color 0.4s ease, background 0.4s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  text-align: center;
}
.result-area.has-result {
  border-color: rgba(255, 209, 102, 0.4);
  border-style: solid;
  background: linear-gradient(135deg, rgba(255, 209, 102, 0.06), rgba(255, 122, 200, 0.06));
}
.result-area.is-miss {
  border-color: rgba(255, 122, 122, 0.35);
  border-style: solid;
  background: linear-gradient(135deg, rgba(255, 122, 122, 0.06), rgba(255, 122, 200, 0.04));
}
.result-placeholder {
  font-size: clamp(0.78rem, 2.4vw, 0.88rem);
  color: #6e7396;
  letter-spacing: 0.08em;
}
.result-miss {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.45rem;
  font-size: clamp(0.78rem, 2.4vw, 0.88rem);
}
.miss-icon {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(255, 122, 122, 0.18);
  color: #ff9b9b;
  font-weight: 800;
  font-size: 0.78rem;
}
.miss-text {
  color: #ffb0b0;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.miss-hint {
  color: #8a8fae;
  font-size: clamp(0.7rem, 2.1vw, 0.78rem);
  letter-spacing: 0.04em;
}
.result-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.meta-item { display: inline-flex; align-items: baseline; gap: 0.45rem; }
.meta-key {
  font-size: clamp(0.68rem, 2.2vw, 0.72rem);
  color: #8a8fae;
  letter-spacing: 0.12em;
  white-space: nowrap;
}
.meta-val {
  font-size: clamp(0.88rem, 2.6vw, 0.95rem);
  font-weight: 600;
  color: #f0f2ff;
}
.result-sources {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.35rem;
  max-width: 100%;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-size: clamp(0.7rem, 2.2vw, 0.78rem);
  background: linear-gradient(135deg, rgba(255, 209, 102, 0.22), rgba(255, 122, 200, 0.22));
  border: 1px solid rgba(255, 209, 102, 0.35);
  color: #ffe7c2;
}
.pill-code { font-weight: 700; letter-spacing: 0.04em; }
.pill-weight { font-variant-numeric: tabular-nums; color: #ffd9a0; }
.pill-ghost {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.18);
  color: #c9cce8;
}
.pill-ghost .pill-weight { color: #b3b8ff; }
.source-divider {
  color: rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}
.source-hint {
  font-size: clamp(0.68rem, 2vw, 0.72rem);
  color: #6e7396;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
}

/* ---------- 拉桿按鈕 ---------- */

.lever-row {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: clamp(0.2rem, 0.8vw, 0.4rem);
}
.lever-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: clamp(0.55rem, 2vw, 0.72rem) clamp(1.2rem, 4.5vw, 1.7rem)
    clamp(0.55rem, 2vw, 0.72rem) clamp(2.4rem, 6.5vw, 3rem);
  font-family: inherit;
  font-size: clamp(0.88rem, 2.6vw, 0.98rem);
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #2a1500;
  background: linear-gradient(180deg, #ffe17a 0%, #ffb02c 60%, #c97a16 100%);
  border: none;
  border-radius: 14px;
  cursor: pointer;
  box-shadow:
    0 12px 28px -10px rgba(255, 176, 44, 0.7),
    inset 0 -3px 0 rgba(0, 0, 0, 0.22),
    inset 0 2px 0 rgba(255, 255, 255, 0.5);
  transition:
    transform 0.15s ease,
    filter 0.2s ease,
    box-shadow 0.3s ease;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}
.lever-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  filter: brightness(1.08);
  box-shadow:
    0 18px 38px -10px rgba(255, 176, 44, 0.85),
    inset 0 -3px 0 rgba(0, 0, 0, 0.22),
    inset 0 2px 0 rgba(255, 255, 255, 0.55);
}
.lever-btn:active:not(:disabled), .lever-btn.is-pulled {
  transform: translateY(2px);
  filter: brightness(0.95);
}
.lever-btn:disabled { cursor: not-allowed; opacity: 0.6; }
.lever-text {
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.35);
}

/* 圓球拉桿頭 */
.lever-knob {
  position: absolute;
  left: clamp(0.45rem, 1.8vw, 0.65rem);
  top: 50%;
  transform: translateY(-50%);
  width: clamp(1.5rem, 4.5vw, 1.85rem);
  height: clamp(1.5rem, 4.5vw, 1.85rem);
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 25%, #ffd4d4 0%, #ff5252 45%, #8a0e0e 100%);
  box-shadow:
    0 4px 10px rgba(0, 0, 0, 0.5),
    inset 0 -3px 6px rgba(0, 0, 0, 0.4),
    inset 0 2px 4px rgba(255, 255, 255, 0.3);
  overflow: hidden;
  transition: transform 0.2s ease;
}
.lever-knob-shine {
  position: absolute;
  top: 18%;
  left: 20%;
  width: 30%;
  height: 30%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.85), transparent 70%);
  filter: blur(2px);
}
.lever-btn:hover:not(:disabled) .lever-knob { transform: translateY(-50%) scale(1.08); }
.lever-btn.is-pulled .lever-knob { transform: translateY(-30%) scale(0.92) rotate(-10deg); }

/* ---------- JACKPOT 飛字 ---------- */

.jackpot-banner {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  z-index: 15;
  pointer-events: none;
}
.jackpot-banner-text {
  font-size: clamp(3rem, 14vw, 6rem);
  font-weight: 900;
  letter-spacing: 0.1em;
  background: linear-gradient(180deg, #fff5d6 0%, #ffd166 40%, #ff7ac8 80%, #ff5577 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  text-shadow:
    0 0 20px rgba(255, 209, 102, 0.6),
    0 0 60px rgba(255, 122, 200, 0.45);
  filter: drop-shadow(0 6px 18px rgba(0, 0, 0, 0.55));
  animation: jackpot-stamp 1.2s cubic-bezier(0.18, 1.5, 0.32, 1);
}
@keyframes jackpot-stamp {
  0% { transform: scale(2.4) rotate(-12deg); opacity: 0; filter: blur(4px) drop-shadow(0 6px 18px rgba(0,0,0,0.55)); }
  25% { transform: scale(0.85) rotate(4deg); opacity: 1; filter: blur(0); }
  45% { transform: scale(1.12) rotate(-3deg); }
  65% { transform: scale(0.97) rotate(1deg); }
  100% { transform: scale(1) rotate(0); }
}
.jackpot-text-enter-active,
.jackpot-text-leave-active { transition: opacity 0.4s ease; }
.jackpot-text-enter-from,
.jackpot-text-leave-to { opacity: 0; }

/* ---------- 彩帶 ---------- */

.confetti {
  position: absolute;
  inset: -24px -24px auto -24px;
  height: 100vh;
  pointer-events: none;
  z-index: 14;
  overflow: hidden;
}
.confetti-piece {
  position: absolute;
  top: -24px;
  border-radius: 2px;
  opacity: 0.95;
  animation-name: confetti-fall;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
  box-shadow: 0 0 6px currentColor;
}
@keyframes confetti-fall {
  0% { transform: translate3d(0, 0, 0) rotate(0deg); opacity: 1; }
  90% { opacity: 0.95; }
  100% { transform: translate3d(40px, 120vh, 0) rotate(900deg); opacity: 0; }
}

/* ---------- 金幣雨 ---------- */

.coins {
  position: absolute;
  inset: -32px -32px auto -32px;
  height: 100vh;
  pointer-events: none;
  z-index: 13;
  overflow: hidden;
}
.coin-piece {
  position: absolute;
  top: -36px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 25%, #fff5d6 0%, #ffd166 45%, #b07a13 100%);
  box-shadow:
    0 0 10px rgba(255, 209, 102, 0.7),
    inset 0 -3px 6px rgba(0, 0, 0, 0.3),
    inset 0 2px 4px rgba(255, 255, 255, 0.4);
  animation-name: coin-fall;
  animation-timing-function: cubic-bezier(0.32, 0.7, 0.42, 1);
  animation-fill-mode: forwards;
}
.coin-piece::after {
  content: '$';
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-weight: 900;
  color: rgba(106, 60, 0, 0.65);
  font-size: 14px;
}
@keyframes coin-fall {
  0% { transform: translate3d(0, 0, 0) rotate(0deg); opacity: 0; }
  10% { opacity: 1; }
  100% { transform: translate3d(var(--drift, 0px), 120vh, 0) rotate(720deg); opacity: 0.5; }
}

/* ---------- 免責 ---------- */

.disclaimer {
  /* 緊貼機台下方，多餘空間留在 disclaimer 之後（底部） */
  margin: 0 auto;
  text-align: center;
  font-size: clamp(0.7rem, 2vw, 0.76rem);
  color: #6e7396;
  line-height: 1.55;
  max-width: 580px;
  flex-shrink: 0;
}

/* ---------- RWD ---------- */

.br-mobile-only { display: none; }

@media (max-width: 540px) {
  /* reel 高度刻意維持 88px 以與 JS 的 ITEM_HEIGHT 同步；
     字級已由 clamp() 自動縮放，不需再覆寫 reel-symbol / reel-name */
  .reel-item { padding: 0.25rem 0.35rem; }
  .br-mobile-only { display: inline; }
  .disclaimer-break { display: none; }
}

@media (max-width: 380px) {
  .machine-sign { letter-spacing: 0.2em; }
  .reels { gap: 0.3rem; }
  .lever-btn { width: 100%; justify-content: center; }
}

/* 視窗高度太矮時，放開 100vh 鎖定，避免內容被壓扁；改用 min-height + 可滾動 */
@media (max-height: 820px) {
  .page {
    height: auto;
    min-height: 100vh;
    min-height: 100dvh;
    overflow: visible;
  }
  .stage { justify-content: flex-start; }
}

/* ---------- 減動效偏好 ----------
 * 注意：拉霸機的「轉動」本身就是這個 feature 的核心體驗，
 * 所以即使啟用「減少動態」也刻意保留 `.reel-strip` 的 transform 過渡，
 * 否則三軸會直接瞬移到終點、整個 view 失去意義。
 * 我們只關掉周邊裝飾類動畫（跑馬燈閃爍、頁面震、彩帶金幣雨等）。
 */
@media (prefers-reduced-motion: reduce) {
  .page.is-rolling .aurora,
  .page.is-jackpot,
  .vegas-rim-gold,
  .vegas-rim-pink,
  .vegas-lights,
  .sign-star,
  .machine-sign.is-jackpot,
  .reel.is-jackpot .reel-window,
  .reel-pay-glow.active,
  .win-line.is-active,
  .jackpot-banner-text,
  .confetti-piece,
  .coin-piece,
  .page-flash {
    animation: none !important;
  }
  .machine.is-jackpot { animation: none !important; }
  .machine.is-miss .machine-frame { animation: none !important; }
  /* 只關掉 sub-pixel shake-y micro 動畫，保留 transform 轉動 */
  .reel.is-spinning .reel-strip { animation: none !important; }
  .page-flash, .confetti, .coins { display: none !important; }
}
</style>
