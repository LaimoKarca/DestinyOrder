<script setup lang="ts">
import { computed } from 'vue'

withDefaults(
  defineProps<{
    /** 滾動中：三軸轉得更快，符合「拉桿」的視覺張力 */
    rolling?: boolean
  }>(),
  { rolling: false },
)

// 多個 SlotIcon 實例若同時存在，clipPath id 不能撞名
const _instance_uid = Math.random().toString(36).slice(2, 9)
const clip_id = computed(() => `slot-clip-${_instance_uid}`)
</script>

<template>
  <span class="slot-icon-wrap" :class="{ rolling }" aria-hidden="true">
    <svg
      class="slot-icon"
      viewBox="0 0 24 24"
      width="22"
      height="22"
    >
      <defs>
        <!-- 三軸視窗：限制符號只在機殼內顯示，超出範圍被裁掉 -->
        <clipPath :id="clip_id">
          <rect x="3.4" y="5.4" width="17.2" height="13.2" />
        </clipPath>
      </defs>

      <!-- 符號層：每軸 5 個橫條符號，CSS 動畫垂直位移 -4 形成無縫循環 -->
      <g :clip-path="`url(#${clip_id})`">
        <g class="reel-col reel-col-1">
          <rect class="reel-sym" x="4.5" y="6" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="4.5" y="10" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="4.5" y="14" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="4.5" y="18" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="4.5" y="22" width="3" height="1.6" rx="0.5" />
        </g>
        <g class="reel-col reel-col-2">
          <rect class="reel-sym" x="10.5" y="6" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="10.5" y="10" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="10.5" y="14" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="10.5" y="18" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="10.5" y="22" width="3" height="1.6" rx="0.5" />
        </g>
        <g class="reel-col reel-col-3">
          <rect class="reel-sym" x="16.5" y="6" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="16.5" y="10" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="16.5" y="14" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="16.5" y="18" width="3" height="1.6" rx="0.5" />
          <rect class="reel-sym" x="16.5" y="22" width="3" height="1.6" rx="0.5" />
        </g>
      </g>

      <!-- 機殼外框與軸分隔線（覆蓋在符號層之上） -->
      <rect
        class="slot-cabinet"
        x="3"
        y="5"
        width="18"
        height="14"
        rx="2"
        fill="none"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <line
        class="slot-divider"
        x1="9"
        y1="5"
        x2="9"
        y2="19"
        stroke-linecap="round"
      />
      <line
        class="slot-divider"
        x1="15"
        y1="5"
        x2="15"
        y2="19"
        stroke-linecap="round"
      />
    </svg>
  </span>
</template>

<style scoped>
.slot-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  position: relative;
  filter: drop-shadow(0 0 3px rgba(94, 200, 255, 0.45));
}

.slot-icon {
  display: block;
  overflow: visible;
}

.slot-cabinet,
.slot-divider {
  stroke: #5ec8ff;
  stroke-width: 2;
  opacity: 0.7;
}

.reel-sym {
  fill: #5ec8ff;
  opacity: 0.75;
}

/* 三軸不同速度，閒置時也持續滾動，明顯有「轉轉轉」感
   符號間距 = 4，位移 -4 完成一個無縫循環 */
.reel-col-1 {
  animation: slot-tick 1.2s linear infinite;
}
.reel-col-2 {
  animation: slot-tick 1.6s linear infinite;
}
.reel-col-3 {
  animation: slot-tick 2s linear infinite;
}

@keyframes slot-tick {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-4px);
  }
}

/* rolling 模式：三軸明顯加速 */
.slot-icon-wrap.rolling .reel-col-1 {
  animation-duration: 0.25s;
}
.slot-icon-wrap.rolling .reel-col-2 {
  animation-duration: 0.35s;
}
.slot-icon-wrap.rolling .reel-col-3 {
  animation-duration: 0.45s;
}
.slot-icon-wrap.rolling {
  filter: drop-shadow(0 0 6px rgba(255, 209, 102, 0.6))
    drop-shadow(0 0 3px rgba(94, 200, 255, 0.55));
}

@media (prefers-reduced-motion: reduce) {
  .reel-col-1,
  .reel-col-2,
  .reel-col-3 {
    animation: none !important;
  }
}
</style>
