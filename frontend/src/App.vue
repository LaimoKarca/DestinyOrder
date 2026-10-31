<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppMenu from '@/components/AppMenu.vue'
import AppFooter from '@/components/AppFooter.vue'
import SpeakerButton from '@/components/SpeakerButton.vue'
import { use_audio_store } from '@/stores/audio'
import { use_dice_favicon } from '@/composables/use_dice_favicon'

const audio_store = use_audio_store()
const route = useRoute()

use_dice_favicon()

// 預設不載入未知權利之第三方背景音樂；若部署者自行提供合法音訊，可透過 VITE_BGM_URL 啟用。
// Web Audio API 即時合成之抽獎 tick / ding / pong 音效不依賴外部音檔，維持正常運作。
const bgm_url =
  (import.meta.env.VITE_BGM_URL as string | undefined)?.trim() ?? ''

onMounted(() => {
  if (bgm_url) {
    audio_store.init_bgm(bgm_url)
  }
})

const DESKTOP_MEDIA_QUERY = '(min-width: 1440px) and (min-height: 800px)'

const is_desktop = ref(false)
let _mql: MediaQueryList | null = null
const _update_is_desktop = (): void => {
  is_desktop.value = _mql?.matches ?? false
}

onMounted(() => {
  _mql = window.matchMedia(DESKTOP_MEDIA_QUERY)
  _update_is_desktop()
  _mql.addEventListener('change', _update_is_desktop)
})

onUnmounted(() => {
  _mql?.removeEventListener('change', _update_is_desktop)
})

// /slot 手機端特殊規則：鎖住整頁捲動，讓拉霸機介面剛好填滿一個視窗。
const is_slot_mobile = computed<boolean>(
  () => !is_desktop.value && route.path === '/slot',
)

watch(
  is_slot_mobile,
  (locked) => {
    if (typeof document === 'undefined') return
    document.documentElement.classList.toggle('app-no-scroll', locked)
  },
  { immediate: true },
)

onUnmounted(() => {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.remove('app-no-scroll')
  }
})
</script>

<template>
  <AppMenu />
  <SpeakerButton />
  <div class="app-layout">
    <RouterView />
  </div>
  <AppFooter />
</template>

<style>
:root {
  color-scheme: dark;
  /* 全站共用：固定 footer 高度，供各 view 在 padding-bottom 中保留空間 */
  --app-footer-height: 2.4rem;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  margin: 0;
  padding: 0;
  min-height: 100%;
  background: #070a1a;
}

/* /slot 手機端鎖住整頁捲動 */
html.app-no-scroll,
html.app-no-scroll body {
  overflow: hidden;
  height: 100%;
}

/* ---------- 全站佈局：100vh 直欄 flex ---------- */
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

.app-layout > main.page {
  min-height: 0 !important;
  flex: 1 0 auto;
}

body {
  font-family:
    'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ---------- 全域 scrollbar：深藍玻璃感（套用到所有捲動容器） ---------- */
/* Firefox */
html {
  scrollbar-width: thin;
  scrollbar-color: rgba(126, 200, 255, 0.45) rgba(11, 15, 36, 0.6);
}

/* WebKit / Chromium */
*::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
*::-webkit-scrollbar-track {
  background: rgba(11, 15, 36, 0.55);
  border-radius: 8px;
}
*::-webkit-scrollbar-thumb {
  background: linear-gradient(
    180deg,
    rgba(126, 200, 255, 0.45),
    rgba(124, 92, 255, 0.45)
  );
  border: 1px solid rgba(179, 184, 255, 0.32);
  border-radius: 8px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.12),
    0 0 8px rgba(126, 200, 255, 0.18);
}
*::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(
    180deg,
    rgba(126, 200, 255, 0.7),
    rgba(124, 92, 255, 0.7)
  );
}
*::-webkit-scrollbar-thumb:active {
  background: linear-gradient(
    180deg,
    rgba(179, 184, 255, 0.9),
    rgba(126, 200, 255, 0.9)
  );
}
*::-webkit-scrollbar-corner {
  background: rgba(11, 15, 36, 0.55);
}
</style>
