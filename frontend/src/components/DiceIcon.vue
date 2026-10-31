<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    rolling?: boolean
    /** 閒置時點數切換間隔（毫秒） */
    idle_interval?: number
    /** 滾動時點數切換間隔（毫秒） */
    roll_interval?: number
    /** 視覺風格：solid（預設立體填色） / outline（海藍透明線框） */
    variant?: 'solid' | 'outline'
  }>(),
  {
    rolling: false,
    idle_interval: 900,
    roll_interval: 80,
    variant: 'solid',
  },
)

const face = ref(6)
let _timer: number | null = null

// 為避免多個 DiceIcon 實例的 <linearGradient id> 撞名，產生 instance-unique id
const _instance_uid = Math.random().toString(36).slice(2, 9)
const body_grad_id = computed(() => `dice-body-${_instance_uid}`)
const sheen_grad_id = computed(() => `dice-sheen-${_instance_uid}`)

function _next_face(): void {
  let nf = face.value
  while (nf === face.value) {
    nf = 1 + Math.floor(Math.random() * 6)
  }
  face.value = nf
}

function _start(interval: number): void {
  _stop()
  _timer = window.setInterval(_next_face, interval)
}

function _stop(): void {
  if (_timer !== null) {
    window.clearInterval(_timer)
    _timer = null
  }
}

watch(
  () => props.rolling,
  (now_rolling) => {
    _start(now_rolling ? props.roll_interval : props.idle_interval)
  },
)

onMounted(() => {
  _start(props.rolling ? props.roll_interval : props.idle_interval)
})

onUnmounted(_stop)

function pip_positions(f: number): Array<[number, number]> {
  const L = 7
  const M = 12
  const R = 17
  const T = 7
  const MD = 12
  const B = 17
  switch (f) {
    case 1:
      return [[M, MD]]
    case 2:
      return [
        [L, T],
        [R, B],
      ]
    case 3:
      return [
        [L, T],
        [M, MD],
        [R, B],
      ]
    case 4:
      return [
        [L, T],
        [R, T],
        [L, B],
        [R, B],
      ]
    case 5:
      return [
        [L, T],
        [R, T],
        [M, MD],
        [L, B],
        [R, B],
      ]
    case 6:
      return [
        [L, T],
        [R, T],
        [L, MD],
        [R, MD],
        [L, B],
        [R, B],
      ]
    default:
      return [[M, MD]]
  }
}
</script>

<template>
  <span class="dice-icon-wrap" :class="[{ rolling }, `variant-${variant}`]" aria-hidden="true">
    <svg
      class="dice-icon"
      viewBox="0 0 24 24"
      width="22"
      height="22"
    >
      <defs>
        <linearGradient :id="body_grad_id" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="100%" stop-color="#cfd4ff" />
        </linearGradient>
        <linearGradient :id="sheen_grad_id" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="rgba(255,255,255,0)" />
          <stop offset="50%" stop-color="rgba(255,255,255,0.85)" />
          <stop offset="100%" stop-color="rgba(255,255,255,0)" />
        </linearGradient>
      </defs>
      <rect
        v-if="variant === 'solid'"
        class="dice-body"
        x="2"
        y="2"
        width="20"
        height="20"
        rx="5"
        :fill="`url(#${body_grad_id})`"
        stroke="#3a3f78"
        stroke-width="1"
      />
      <rect
        v-if="variant === 'solid'"
        class="dice-sheen"
        x="2"
        y="2"
        width="20"
        height="20"
        rx="5"
        :fill="`url(#${sheen_grad_id})`"
      />
      <rect
        v-else
        class="dice-body-outline"
        x="2.5"
        y="2.5"
        width="19"
        height="19"
        rx="4.5"
        fill="none"
        stroke="#5EC8FF"
        stroke-width="2"
        stroke-linejoin="round"
        opacity="0.7"
      />
      <g
        class="dice-pips"
        :fill="variant === 'solid' ? '#1a1f3a' : '#5EC8FF'"
        :opacity="variant === 'solid' ? 1 : 0.7"
      >
        <circle
          v-for="(pos, i) in pip_positions(face)"
          :key="i"
          :cx="pos[0]"
          :cy="pos[1]"
          r="1.7"
        />
      </g>
    </svg>
  </span>
</template>

<style scoped>
.dice-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  position: relative;
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.55));
  animation: dice-idle-bob 1.6s ease-in-out infinite;
}
.dice-icon-wrap.variant-outline {
  filter: drop-shadow(0 0 3px rgba(94, 200, 255, 0.45));
}

.dice-icon {
  display: block;
  overflow: visible;
}

/* 閒置：微微上下浮動 + 輕度搖擺，營造「躍躍欲試」感 */
@keyframes dice-idle-bob {
  0%,
  100% {
    transform: translateY(0) rotate(-4deg);
  }
  50% {
    transform: translateY(-1.5px) rotate(4deg);
  }
}

/* 高光斜掃動畫：金屬感的反光不停滑過 */
.dice-sheen {
  transform-origin: center;
  mix-blend-mode: screen;
  animation: dice-sheen-sweep 2.4s ease-in-out infinite;
}
@keyframes dice-sheen-sweep {
  0% {
    opacity: 0;
    transform: translateX(-12px);
  }
  35% {
    opacity: 0.9;
  }
  60% {
    opacity: 0.6;
  }
  100% {
    opacity: 0;
    transform: translateX(12px);
  }
}

/* 點數每次更新的微彈效果 */
.dice-pips {
  transform-origin: 12px 12px;
  animation: pip-pop 0.18s ease-out;
}
@keyframes pip-pop {
  0% {
    transform: scale(0.55);
    opacity: 0.4;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

/* 滾動中：快速旋轉 + 更亮的光暈 */
.dice-icon-wrap.rolling {
  animation: dice-roll-spin 0.32s linear infinite;
  filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.9))
    drop-shadow(0 0 14px rgba(126, 200, 255, 0.7));
}
@keyframes dice-roll-spin {
  0% {
    transform: rotate(0) scale(1);
  }
  50% {
    transform: rotate(180deg) scale(1.18);
  }
  100% {
    transform: rotate(360deg) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .dice-icon-wrap,
  .dice-icon-wrap.rolling,
  .dice-sheen,
  .dice-pips {
    animation: none !important;
  }
}
</style>
