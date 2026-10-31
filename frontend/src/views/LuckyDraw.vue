<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { DrawableStock } from '@/types/funds'
import { pick_random_stock } from '@/services/funds'
import { use_funds_store } from '@/stores/funds'
import { use_audio_store } from '@/stores/audio'
import DiceIcon from '@/components/DiceIcon.vue'

const ETF_ORDER = ['0050', '006208', '009816', '00403A', '00981A'] as const

const store = use_funds_store()
const audio_store = use_audio_store()
const { stocks: pool, data_date: dataDate, loading, error } = storeToRefs(store)

const result = ref<DrawableStock | null>(null)
const rolling = ref(false)
const revealing = ref(false)
const rollingPreview = ref<DrawableStock | null>(null)
const hasDrawn = ref(false)

/**
 * 改用 Array 來記錄篩選狀態，以完美適配 Vue 原生的 checkbox v-model 多選綁定
 */
const etf_filter = ref<string[]>([...ETF_ORDER])

// 下拉選單狀態與 DOM 參考
const isDropdownOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

// Vegas 跑馬燈：onMount 就量測 .card 並啟動 ResizeObserver，
// 確保 rolling 切到 true 的當下 vegas_dims 已經是有效值（避免 v-if 延遲一幀的空窗）
const card_ref = ref<HTMLElement | null>(null)
const vegas_dims = ref({ w: 0, h: 0 })
let _vegas_resize_obs: ResizeObserver | null = null

const VEGAS_OUTSET = 10

function _measure_vegas(): void {
  if (!card_ref.value) return
  const r = card_ref.value.getBoundingClientRect()
  if (r.width <= 0 || r.height <= 0) return
  vegas_dims.value = {
    w: Math.round(r.width + VEGAS_OUTSET * 2),
    h: Math.round(r.height + VEGAS_OUTSET * 2),
  }
}

/**
 * 處理全選/取消全選的雙向綁定邏輯
 */
const isAllSelected = computed({
  get: () => etf_filter.value.length === ETF_ORDER.length,
  set: (val: boolean) => {
    if (val) {
      etf_filter.value = [...ETF_ORDER]
    } else {
      etf_filter.value = []
    }
  }
})

/**
 * 根據所選 ETF 過濾抽獎池
 */
const filtered_pool = computed(() => {
  if (etf_filter.value.length === 0) return []
  return pool.value.filter((stock) => {
    return stock.sources.some((x) => etf_filter.value.includes(x.etf_code))
  })
})

const groupedSources = computed(() => {
  if (!result.value) return { selected: [], unselected: [] }

  const selected: typeof result.value.sources = []
  const unselected: typeof result.value.sources = []

  // 先依照 ETF_ORDER 進行排序
  const sorted = [...result.value.sources].sort(
    (a, b) =>
      ETF_ORDER.indexOf(a.etf_code as (typeof ETF_ORDER)[number]) -
      ETF_ORDER.indexOf(b.etf_code as (typeof ETF_ORDER)[number]),
  )

  // 依據是否有在篩選清單內，分發至不同陣列
  for (const src of sorted) {
    if (etf_filter.value.includes(src.etf_code)) {
      selected.push(src)
    } else {
      unselected.push(src)
    }
  }

  return { selected, unselected }
})

let audio_ctx: AudioContext | null = null

function prefers_reduced_motion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
  )
}

function ensure_audio_ctx(): AudioContext | null {
  if (typeof window === 'undefined') return null
  try {
    const Ctor =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext
    if (!Ctor) return null
    audio_ctx ??= new Ctor()
    return audio_ctx
  } catch {
    return null
  }
}

/** * Synthesize a kick-drum-style "PONG": sub-bass sine sweep + transient noise burst. 
 */
function play_pong(): void {
  if (prefers_reduced_motion()) return
  const ctx = ensure_audio_ctx()
  if (!ctx) return
  try {
    const now = ctx.currentTime

    // 1) Bass body
    const body_osc = ctx.createOscillator()
    const body_gain = ctx.createGain()
    body_osc.type = 'sine'
    body_osc.frequency.setValueAtTime(180, now)
    body_osc.frequency.exponentialRampToValueAtTime(38, now + 0.32)
    body_gain.gain.setValueAtTime(0.0001, now)
    body_gain.gain.exponentialRampToValueAtTime(0.9, now + 0.006)
    body_gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.55)
    body_osc.connect(body_gain).connect(ctx.destination)
    body_osc.start(now)
    body_osc.stop(now + 0.6)

    // 2) Click transient
    const sample_count = Math.floor(ctx.sampleRate * 0.04)
    const buf = ctx.createBuffer(1, sample_count, ctx.sampleRate)
    const data = buf.getChannelData(0)
    for (let i = 0; i < sample_count; i++) {
      data[i] =
        (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.008))
    }
    const noise = ctx.createBufferSource()
    noise.buffer = buf
    const noise_gain = ctx.createGain()
    noise_gain.gain.value = 0.28
    noise.connect(noise_gain).connect(ctx.destination)
    noise.start(now)

    // 3) Boom tail
    const tail_osc = ctx.createOscillator()
    const tail_gain = ctx.createGain()
    tail_osc.type = 'sine'
    tail_osc.frequency.setValueAtTime(60, now)
    tail_osc.frequency.exponentialRampToValueAtTime(28, now + 0.5)
    tail_gain.gain.setValueAtTime(0.0001, now)
    tail_gain.gain.exponentialRampToValueAtTime(0.35, now + 0.02)
    tail_gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.7)
    tail_osc.connect(tail_gain).connect(ctx.destination)
    tail_osc.start(now)
    tail_osc.stop(now + 0.75)
  } catch {
    // ignore audio failures
  }
}

function buzz(): void {
  if (prefers_reduced_motion()) return
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    try {
      navigator.vibrate?.([55, 30, 25])
    } catch {
      // ignore
    }
  }
}

/**
 * 監聽外部點擊事件以關閉下拉選單
 */
function handle_click_outside(event: MouseEvent): void {
  if (
    isDropdownOpen.value &&
    dropdownRef.value &&
    !dropdownRef.value.contains(event.target as Node)
  ) {
    isDropdownOpen.value = false
  }
}

// card_ref 要等 loading 結束才掛載，所以等 ref 出現後再啟動觀察
watch(card_ref, (el) => {
  _vegas_resize_obs?.disconnect()
  _vegas_resize_obs = null
  if (el && typeof ResizeObserver !== 'undefined') {
    _measure_vegas()
    _vegas_resize_obs = new ResizeObserver(_measure_vegas)
    _vegas_resize_obs.observe(el)
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
})

/**
 * 執行抽獎邏輯
 */
async function draw() {
  if (rolling.value || revealing.value || filtered_pool.value.length === 0) return
  rolling.value = true
  result.value = null
  isDropdownOpen.value = false // 抽獎時自動關閉選單

  const totalMs = 1800
  const startInterval = 50
  const endInterval = 140
  const start = performance.now()

  await new Promise<void>((resolve) => {
    function tick() {
      const elapsed = performance.now() - start
      const progress = Math.min(elapsed / totalMs, 1)
      const interval =
        startInterval + (endInterval - startInterval) * (progress * progress)
      rollingPreview.value = pick_random_stock(filtered_pool.value)
      audio_store.play_tick()

      if (progress >= 1) {
        const final = pick_random_stock(filtered_pool.value)
        result.value = final
        rollingPreview.value = final
        rolling.value = false
        hasDrawn.value = true
        resolve()
        return
      }
      window.setTimeout(tick, interval)
    }
    tick()
  })

  revealing.value = true
  play_pong()
  audio_store.play_ding()
  buzz()
  window.setTimeout(() => {
    revealing.value = false
  }, 780)
}
</script>

<template>
  <main
    class="page"
    :class="{ 'is-rolling': rolling, 'is-revealing': revealing }"
  >
    <div class="aurora" aria-hidden="true"></div>
    <div v-if="revealing" class="page-flash" aria-hidden="true"></div>

    <header class="hero">
      <span class="eyebrow">DestinyOrder · 命定抽選</span>
      <h1>台股 ETF 抽抽樂</h1>
      <p class="subtitle">
        匯集 0050 / 006208 / 009816 / 00403A / 00981A<br class="br-mobile-only" /> 五檔 ETF 的成分股，<br class="br-desktop-only" />
        隨機抽出一檔讓命運為選股。
      </p>
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
        <div
          ref="card_ref"
          class="card"
          :class="{
            'is-rolling': rolling,
            'is-revealing': revealing,
            'has-result': result && !rolling && !revealing,
          }"
        >
          <div class="card-fx" aria-hidden="true">
            <div class="card-glow" />
            <div v-if="rolling" class="card-rings">
              <span class="ring ring-1" />
              <span class="ring ring-2" />
              <span class="ring ring-3" />
            </div>
            <div v-if="revealing" class="shockwave">
              <span class="wave wave-1" />
              <span class="wave wave-2" />
            </div>
          </div>

          <div
            v-show="rolling && vegas_dims.w > 0"
            class="vegas-lights"
            :style="{
              width: vegas_dims.w + 'px',
              height: vegas_dims.h + 'px',
            }"
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
                rx="30"
                ry="30"
                vector-effect="non-scaling-stroke"
              />
            </svg>
          </div>

<div class="card-top">
            <div class="card-header-row">
              <span class="card-label">命運標的</span>
              
              <span class="dropdown-container" ref="dropdownRef">
                <button 
                  type="button" 
                  class="dropdown-toggle" 
                  @click="isDropdownOpen = !isDropdownOpen"
                  :aria-expanded="isDropdownOpen"
                >
                  {{ etf_filter.length === ETF_ORDER.length ? '篩選：全部' : `篩選 ${etf_filter.length} 檔` }}
                  <span class="arrow" :class="{ open: isDropdownOpen }">▼</span>
                </button>
                
                <div v-show="isDropdownOpen" class="dropdown-menu">
                  <label class="dropdown-item">
                    <input type="checkbox" v-model="isAllSelected" />
                    全部
                  </label>
                  <label v-for="code in ETF_ORDER" :key="code" class="dropdown-item">
                    <input 
                      type="checkbox" 
                      :value="code"
                      v-model="etf_filter"
                    />
                    {{ code }}
                  </label>
                </div>
              </span>
            </div>

            <div class="card-sources">
              <template v-if="result && !rolling">
                <span
                  v-for="src in groupedSources.selected"
                  :key="src.etf_code"
                  class="pill"
                  :title="`${src.etf_name} · 權重 ${src.weight}`"
                >
                  <span class="pill-code">{{ src.etf_code }}</span>
                  <span class="pill-weight">{{ src.weight }}</span>
                </span>

                <template v-if="groupedSources.unselected.length > 0">
                  <span class="source-divider">|</span>
                  <span class="source-hint">其他收錄 </span>
                  <span
                    v-for="src in groupedSources.unselected"
                    :key="src.etf_code"
                    class="pill pill-ghost"
                    :title="`${src.etf_name} · 權重 ${src.weight}`"
                  >
                    <span class="pill-code">{{ src.etf_code }}</span>
                    <span class="pill-weight">{{ src.weight }}</span>
                  </span>
                </template>
              </template>
              <span v-else class="pill pill-ghost">— 等待開獎 —</span>
            </div>
          </div>
          <div class="card-body">
            <div class="block" :class="{ rolling, revealing }">
              <div class="block-name">
                {{ (rollingPreview ?? result)?.name ?? '？？？' }}
              </div>
              <div class="block-meta">
                <span class="meta-item">
                  <span class="meta-key">代號</span>
                  <span class="meta-val">{{
                    (rollingPreview ?? result)?.symbol ?? '——'
                  }}</span>
                </span>
                <span class="meta-divider" />
                <span class="meta-item">
                  <span class="meta-key">產業別</span>
                  <span class="meta-val">{{
                    (rollingPreview ?? result)?.industry ?? '未分類'
                  }}</span>
                </span>
              </div>
            </div>
          </div>

          <div class="card-actions">
            <button
              type="button"
              class="draw-btn"
              :disabled="rolling || revealing || filtered_pool.length === 0"
              @click="draw"
            >
              <DiceIcon class="draw-btn-icon" :rolling="rolling" />
              <span class="draw-btn-text">
                {{ rolling ? '抽取中…' : hasDrawn ? '再抽一次' : '開始抽抽' }}
              </span>
            </button>
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
  min-height: 100vh;
  min-height: 100dvh;
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
  overflow-x: hidden;
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
  transition: filter 0.3s ease;
}

.page.is-rolling .aurora {
  animation: aurora-rage 0.55s ease-in-out infinite alternate;
  filter: saturate(1.4) brightness(1.3);
}
@keyframes aurora-rage {
  from {
    transform: scale(1);
    opacity: 0.85;
  }
  to {
    transform: scale(1.06);
    opacity: 1.2;
  }
}

.page.is-revealing {
  animation: page-quake 0.46s cubic-bezier(0.36, 0.07, 0.19, 0.97);
}
@keyframes page-quake {
  0% {
    transform: translate3d(0, 0, 0);
  }
  10% {
    transform: translate3d(-4px, 2px, 0);
  }
  20% {
    transform: translate3d(5px, -3px, 0);
  }
  30% {
    transform: translate3d(-6px, 3px, 0);
  }
  40% {
    transform: translate3d(4px, -2px, 0);
  }
  50% {
    transform: translate3d(-3px, 2px, 0);
  }
  60% {
    transform: translate3d(2px, -1px, 0);
  }
  70% {
    transform: translate3d(-2px, 1px, 0);
  }
  80% {
    transform: translate3d(1px, -1px, 0);
  }
  100% {
    transform: translate3d(0, 0, 0);
  }
}

.page-flash {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(
      circle at 50% 50%,
      rgba(255, 255, 255, 0.55) 0%,
      rgba(179, 184, 255, 0.25) 30%,
      transparent 70%
    );
  pointer-events: none;
  z-index: 9999;
  animation: page-flash 0.42s ease-out forwards;
  mix-blend-mode: screen;
}
@keyframes page-flash {
  0% {
    opacity: 0.95;
  }
  40% {
    opacity: 0.5;
  }
  100% {
    opacity: 0;
  }
}

.hero {
  position: relative;
  max-width: 720px;
  margin: 0 auto clamp(1.6rem, 4vw, 2.5rem);
  text-align: center;
}

.eyebrow {
  display: inline-block;
  padding: 0.35rem 0.9rem;
  font-size: clamp(0.7rem, 2.4vw, 0.78rem);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #c9c6f6;
}

.hero h1 {
  margin: 0.9rem 0 0.6rem;
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
  margin: 0 auto;
  max-width: 540px;
  color: #b1b6d6;
  font-size: clamp(0.88rem, 2.6vw, 0.98rem);
  line-height: 1.7;
}

.stage {
  position: relative;
  max-width: 720px;
  margin: 0 auto;
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

/* ---------- 卡片本體 ---------- */

.card {
  position: relative;
  border-radius: clamp(16px, 3vw, 22px);
  /* 修正處：將原先 padding 上下減半，左右不變 */
  padding: clamp(0.55rem, 2vw, 1.1rem) clamp(1.1rem, 4vw, 2.2rem);
  background:
    linear-gradient(
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
  transition:
    transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 0.5s ease;
  /* 移除 overflow: hidden; 釋放下拉選單邊界 */
}

/* 新增獨立的特效層，承載隱藏溢出邊界的任務 */
.card-fx {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.card.has-result {
  transform: translateY(-2px);
  box-shadow:
    0 40px 70px -30px rgba(83, 110, 255, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.card.is-rolling {
  animation:
    card-breathing 0.42s ease-in-out infinite alternate,
    card-jitter 0.09s linear infinite;
  border-color: rgba(179, 184, 255, 0.45);
  box-shadow:
    0 30px 60px -10px rgba(83, 110, 255, 0.55),
    0 0 0 1px rgba(179, 184, 255, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
@keyframes card-breathing {
  from {
    transform: scale(1);
  }
  to {
    transform: scale(1.018);
  }
}
@keyframes card-jitter {
  0% {
    margin-left: 0;
  }
  25% {
    margin-left: -1px;
  }
  50% {
    margin-left: 0;
  }
  75% {
    margin-left: 1px;
  }
  100% {
    margin-left: 0;
  }
}

.card.is-revealing {
  animation: card-slam 0.72s cubic-bezier(0.22, 1.5, 0.32, 1) forwards;
  box-shadow:
    0 60px 90px -20px rgba(126, 200, 255, 0.7),
    0 0 0 2px rgba(255, 255, 255, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
@keyframes card-slam {
  0% {
    transform: scale(1.12) translateY(-6px);
  }
  35% {
    transform: scale(0.94) translateY(6px);
  }
  55% {
    transform: scale(1.03) translateY(-2px);
  }
  75% {
    transform: scale(0.99) translateY(1px);
  }
  100% {
    transform: scale(1) translateY(0);
  }
}

/* ---------- 卡內光暈與圓環 ---------- */

.card-glow {
  position: absolute;
  inset: -40%;
  background: conic-gradient(
    from 0deg,
    rgba(126, 200, 255, 0) 0deg,
    rgba(126, 200, 255, 0.18) 90deg,
    rgba(179, 184, 255, 0.18) 180deg,
    rgba(255, 122, 200, 0.15) 270deg,
    rgba(126, 200, 255, 0) 360deg
  );
  filter: blur(40px);
  opacity: 0;
  transition: opacity 0.6s ease;
  z-index: 0;
}
.card.has-result .card-glow {
  opacity: 0.9;
  animation: rotate 8s linear infinite;
}

.card.is-rolling .card-glow {
  opacity: 1;
  animation:
    rotate 1.1s linear infinite,
    glow-burst 0.32s ease-in-out infinite alternate;
}
@keyframes glow-burst {
  from {
    filter: blur(38px) brightness(1.1) saturate(1.2);
  }
  to {
    filter: blur(64px) brightness(1.9) saturate(1.8);
  }
}

.card.is-revealing .card-glow {
  opacity: 1;
  animation: glow-impact 0.72s ease-out forwards;
}
@keyframes glow-impact {
  0% {
    filter: blur(80px) brightness(2.6) saturate(2);
    opacity: 1;
  }
  60% {
    filter: blur(60px) brightness(1.4) saturate(1.4);
    opacity: 0.95;
  }
  100% {
    filter: blur(40px) brightness(1) saturate(1);
    opacity: 0.9;
  }
}

@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}

.card-rings {
  position: absolute;
  inset: 0;
  z-index: 0;
  mix-blend-mode: screen;
}
.ring {
  position: absolute;
  inset: -10%;
  border-radius: 50%;
  filter: blur(6px);
}
.ring-1 {
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    rgba(126, 200, 255, 0.55) 60deg,
    transparent 140deg,
    rgba(179, 184, 255, 0.6) 240deg,
    transparent 320deg
  );
  animation: rotate 0.55s linear infinite;
}
.ring-2 {
  inset: 5%;
  background: conic-gradient(
    from 180deg,
    transparent 0deg,
    rgba(255, 122, 200, 0.45) 50deg,
    transparent 130deg,
    rgba(255, 218, 121, 0.4) 230deg,
    transparent 310deg
  );
  animation: rotate-rev 0.42s linear infinite;
}
.ring-3 {
  inset: 18%;
  background: conic-gradient(
    from 90deg,
    transparent 0deg,
    rgba(180, 255, 200, 0.4) 70deg,
    transparent 150deg,
    rgba(126, 200, 255, 0.4) 250deg,
    transparent 330deg
  );
  animation: rotate 0.28s linear infinite;
}
@keyframes rotate-rev {
  to {
    transform: rotate(-360deg);
  }
}

.shockwave {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
}
.wave {
  position: absolute;
  border-radius: 50%;
  border: 3px solid rgba(179, 184, 255, 0.8);
  box-shadow: 0 0 30px rgba(126, 200, 255, 0.6);
  width: 0;
  height: 0;
}
.wave-1 {
  animation: wave-expand 0.7s cubic-bezier(0.18, 0.84, 0.34, 1) forwards;
}
.wave-2 {
  border-color: rgba(255, 255, 255, 0.6);
  animation: wave-expand 0.78s cubic-bezier(0.18, 0.84, 0.34, 1) 0.1s forwards;
}
@keyframes wave-expand {
  0% {
    width: 0;
    height: 0;
    opacity: 1;
    border-width: 8px;
  }
  60% {
    opacity: 0.65;
    border-width: 3px;
  }
  100% {
    width: 140%;
    height: 140%;
    opacity: 0;
    border-width: 1px;
  }
}

/* ---------- Vegas 跑馬燈：卡片四周環繞繞圈圈的賭場燈泡 ---------- */

.vegas-lights {
  position: absolute;
  top: -10px;
  left: -10px;
  /* width/height 由 :style 動態灌入，避免 inset/百分比解析失敗 */
  pointer-events: none;
  z-index: 3;
  animation: vegas-pulse 0.6s ease-in-out infinite alternate;
}

.vegas-svg {
  display: block;
  /* drop-shadow 暈光必須跨出 SVG 邊界 */
  overflow: visible;
}

.vegas-rim {
  fill: none;
  stroke-linecap: round;
  /* dash 12px、gap 14px：長條膠囊狀光珠，避免短點 flicker */
  stroke-dasharray: 12 14;
}

.vegas-rim-gold {
  stroke: #ffd166;
  stroke-width: 4.5;
  /* 1.8s 對齊 draw() 的 totalMs；用標準 ease-out 讓變化平緩，
     不會像強 cubic-bezier 那樣前段衝太快、後段拖太久 */
  animation: vegas-chase-decelerate 1.8s ease-out forwards;
  filter:
    drop-shadow(0 0 6px #ffd166)
    drop-shadow(0 0 14px rgba(255, 209, 102, 0.6));
}

@keyframes vegas-chase-decelerate {
  from {
    stroke-dashoffset: 0;
  }
  to {
    /* -390 = 15 個 dash+gap 週期；增加總位移讓平均流速接近原本的 linear 觀感 */
    stroke-dashoffset: -390;
  }
}

@keyframes vegas-pulse {
  from {
    filter: brightness(0.95) saturate(1);
  }
  to {
    filter: brightness(1.25) saturate(1.4);
  }
}

/* ---------- 卡片內容 ---------- */

.card-top {
  position: relative;
  z-index: 10; /* 關鍵修正：單獨拉高 card-top 層級，確保下拉選單能接收點擊 */
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: clamp(1rem, 3vw, 1.4rem);
}

.card-body,
.card-actions {
  position: relative;
  z-index: 1;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-label {
  font-size: clamp(0.7rem, 2.4vw, 0.75rem);
  letter-spacing: 0.22em;
  color: #8a8fae;
  text-transform: uppercase;
}

/* ---------- 下拉選單樣式 ---------- */
.dropdown-container {
  position: relative;
  display: inline-block;
}

.dropdown-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: transparent;
  border: none;
  color: #6e7396;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: clamp(0.7rem, 2.4vw, 0.75rem);
  font-weight: 500;
  letter-spacing: 0.05em;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}

.dropdown-toggle:hover {
  color: #8a8fae;
  background: rgba(255, 255, 255, 0.04);
}

.arrow {
  font-size: 0.6rem;
  transition: transform 0.2s ease;
}

.arrow.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.4rem);
  right: 0;
  background: rgba(11, 15, 36, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(179, 184, 255, 0.25);
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

.dropdown-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.dropdown-item input[type="checkbox"] {
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

.dropdown-item input[type="checkbox"]::before {
  content: "";
  width: 0.65em;
  height: 0.65em;
  transform: scale(0);
  transition: 120ms transform ease-in-out;
  box-shadow: inset 1em 1em #fff;
  background-color: CanvasText;
  transform-origin: center;
  clip-path: polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 43% 62%);
}

.dropdown-item input[type="checkbox"]:checked {
  background-color: #7ec8ff;
  border-color: #7ec8ff;
}

.dropdown-item input[type="checkbox"]:checked::before {
  transform: scale(1);
}

.card-sources {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  min-height: 28px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: clamp(0.72rem, 2.4vw, 0.78rem);
  background: linear-gradient(
    135deg,
    rgba(126, 200, 255, 0.18),
    rgba(124, 92, 255, 0.18)
  );
  border: 1px solid rgba(179, 184, 255, 0.28);
  color: #e2e6ff;
}
.pill-code {
  font-weight: 700;
  letter-spacing: 0.04em;
}
.pill-weight {
  font-variant-numeric: tabular-nums;
  color: #b3b8ff;
}
.pill-ghost {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(179, 184, 255, 0.2);
  color: #c9cce8;
}

.source-divider {
  color: rgba(255, 255, 255, 0.15);
  margin: 0 0.1rem;
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

.card-body {
  padding: clamp(1rem, 3vw, 1.4rem) 0 clamp(0.8rem, 3vw, 1.2rem);
  text-align: center;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
  border-bottom: 1px dashed rgba(255, 255, 255, 0.08);
}

.block {
  transition:
    transform 0.25s ease,
    filter 0.25s ease;
}

.block.rolling {
  animation: shake-hard 0.11s linear infinite;
  filter: blur(0.6px) saturate(1.3);
}
@keyframes shake-hard {
  0% {
    transform: translate(-2px, 1px) rotate(-1deg);
  }
  20% {
    transform: translate(3px, -2px) rotate(1.2deg);
  }
  40% {
    transform: translate(-3px, 2px) rotate(-0.6deg);
  }
  60% {
    transform: translate(2px, -1px) rotate(0.8deg);
  }
  80% {
    transform: translate(-1px, -2px) rotate(-1deg);
  }
  100% {
    transform: translate(2px, 2px) rotate(1deg);
  }
}

.block.revealing {
  animation: block-land 0.5s cubic-bezier(0.2, 1.5, 0.32, 1) forwards;
}
@keyframes block-land {
  0% {
    transform: translateY(-8px) scale(1.05);
  }
  50% {
    transform: translateY(4px) scale(0.97);
  }
  100% {
    transform: translateY(0) scale(1);
  }
}

.block-name {
  font-size: clamp(1.8rem, 7vw, 2.8rem);
  font-weight: 800;
  letter-spacing: 0.04em;
  background: linear-gradient(180deg, #fff 0%, #c2c7f0 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  min-height: 2.6rem;
  word-break: break-word;
  transition: text-shadow 0.3s ease;
}

.block.revealing .block-name {
  animation: stamp 0.6s cubic-bezier(0.18, 1.5, 0.32, 1) forwards;
  text-shadow:
    0 0 20px rgba(179, 184, 255, 0.8),
    0 0 40px rgba(126, 200, 255, 0.5);
}
@keyframes stamp {
  0% {
    transform: scale(1.55);
    letter-spacing: 0.18em;
    filter: blur(2px);
  }
  40% {
    transform: scale(0.9);
    letter-spacing: 0.02em;
    filter: blur(0);
  }
  70% {
    transform: scale(1.04);
  }
  100% {
    transform: scale(1);
    letter-spacing: 0.04em;
  }
}

.block-meta {
  display: inline-flex;
  align-items: center;
  gap: 1rem;
  margin-top: clamp(0.7rem, 2.5vw, 0.9rem);
  padding: 0.55rem 1rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  max-width: 100%;
}
.meta-item {
  display: inline-flex;
  align-items: baseline;
  gap: 0.45rem;
}
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
  font-variant-numeric: tabular-nums;
}
.meta-divider {
  width: 1px;
  align-self: stretch;
  background: rgba(255, 255, 255, 0.08);
}

/* ---------- 抽抽按鈕 ---------- */

.card-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: clamp(1rem, 3vw, 1.4rem);
}

.draw-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: clamp(0.7rem, 2.6vw, 0.85rem) clamp(1.4rem, 5vw, 1.8rem);
  font-size: clamp(0.92rem, 2.8vw, 1rem);
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #0b0f24;
  background: linear-gradient(135deg, #b3b8ff 0%, #7ec8ff 100%);
  border: none;
  border-radius: 14px;
  cursor: pointer;
  box-shadow:
    0 10px 25px -10px rgba(179, 184, 255, 0.6),
    inset 0 -2px 0 rgba(0, 0, 0, 0.12);
  transition:
    transform 0.15s ease,
    box-shadow 0.3s ease,
    filter 0.2s ease;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}
.draw-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  filter: brightness(1.06);
  box-shadow:
    0 16px 35px -10px rgba(179, 184, 255, 0.7),
    inset 0 -2px 0 rgba(0, 0, 0, 0.15);
}
.draw-btn:active:not(:disabled) {
  transform: translateY(0);
}
.draw-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.draw-btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.disclaimer {
  margin-top: clamp(1.1rem, 3.5vw, 1.5rem);
  text-align: center;
  font-size: clamp(0.72rem, 2.4vw, 0.78rem);
  color: #6e7396;
  line-height: 1.6;
}

/* ---------- RWD breakpoints ---------- */

/* 桌機限定的換行 / 手機限定的換行（用 class 切換顯示） */
.br-mobile-only {
  display: none;
}
.br-desktop-only {
  display: inline;
}

@media (max-width: 768px) {
  .hero {
    margin-bottom: 1.6rem;
  }
}

@media (max-width: 540px) {
  .block-meta {
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.7rem 1rem;
    width: 100%;
  }
  .meta-divider {
    display: none;
  }
  .meta-item {
    justify-content: center;
  }
  /* 手機翻轉：桌機 <br> 關掉、手機 <br> 開啟 */
  .br-desktop-only {
    display: none;
  }
  .br-mobile-only {
    display: inline;
  }
  /* 手機版免責聲明併為一段，不強制換行 */
  .disclaimer-break {
    display: none;
  }
}

@media (max-width: 360px) {
  .hero h1 {
    font-size: 1.6rem;
  }
  .card {
    padding: 1rem;
  }
  .draw-btn {
    width: 100%;
    justify-content: center;
  }
}

@media (min-width: 1280px) {
  .card.has-result {
    box-shadow:
      0 50px 90px -30px rgba(83, 110, 255, 0.6),
      inset 0 1px 0 rgba(255, 255, 255, 0.06);
  }
}

/* 系統偏好減少動態時，停掉所有滾動 / 衝擊 / 抖動動畫 */
@media (prefers-reduced-motion: reduce) {
  .page.is-revealing,
  .page.is-rolling .aurora,
  .card.is-rolling,
  .card.is-rolling .card-glow,
  .card.is-revealing,
  .card.is-revealing .card-glow,
  .block.rolling,
  .block.revealing,
  .block.revealing .block-name,
  .page-flash,
  .card-rings,
  .shockwave,
  .ring,
  .wave,
  .spinner {
    animation: none !important;
  }
  .page-flash,
  .card-rings,
  .shockwave {
    display: none !important;
  }
  .card {
    transition: none;
  }
}
</style>