<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { use_audio_store } from '@/stores/audio'

const store = use_audio_store()
const { muted } = storeToRefs(store)

const aria_label = computed(() => (muted.value ? '取消靜音' : '靜音'))
</script>

<template>
  <button
    type="button"
    class="speaker-btn"
    :class="{ 'is-muted': muted }"
    :aria-label="aria_label"
    :title="aria_label"
    @click="store.toggle_muted"
  >
    <svg
      class="speaker-icon"
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
    >
      <path
        d="M4 9.5v5h3.5L12 18.5V5.5L7.5 9.5H4z"
        fill="currentColor"
      />
      <g
        v-if="!muted"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linecap="round"
        fill="none"
      >
        <path d="M15.5 9c1.4 1.5 1.4 4.5 0 6" />
        <path d="M18 6.5c2.4 2.3 2.4 8.7 0 11" />
      </g>
      <g
        v-else
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      >
        <line x1="16" y1="9" x2="21" y2="14" />
        <line x1="21" y1="9" x2="16" y2="14" />
      </g>
    </svg>
  </button>
</template>

<style scoped>
.speaker-btn {
  position: fixed;
  top: clamp(0.8rem, 2.5vw, 1.4rem);
  right: clamp(0.8rem, 2.5vw, 1.4rem);
  z-index: 60;
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(11, 15, 36, 0.65);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #e8eaf6;
  cursor: pointer;
  transition:
    background 0.25s ease,
    border-color 0.25s ease,
    transform 0.18s ease,
    color 0.25s ease;
  -webkit-tap-highlight-color: transparent;
}

.speaker-btn:hover {
  background: rgba(126, 200, 255, 0.2);
  border-color: rgba(179, 184, 255, 0.45);
}

.speaker-btn:active {
  transform: scale(0.94);
}

.speaker-btn.is-muted {
  color: #ff9a9a;
  border-color: rgba(255, 154, 154, 0.4);
  background: rgba(45, 12, 22, 0.55);
}

.speaker-icon {
  display: block;
}

@media (prefers-reduced-motion: reduce) {
  .speaker-btn {
    transition: none;
  }
}
</style>
