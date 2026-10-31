<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import DiceIcon from '@/components/DiceIcon.vue'
import SlotIcon from '@/components/SlotIcon.vue'

interface NavItem {
  to: string
  label: string
  description: string
  icon: string
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    label: '命定抽選',
    description: '隨機抽出一檔 ETF 成分股',
    icon: 'dice',
  },
  {
    to: '/slot',
    label: '命定拉霸機',
    description: '三軸同框、命中三連即定',
    icon: 'slot',
  },
  {
    to: '/holdings',
    label: '成分股一覽',
    description: '五檔 ETF 持股對照表',
    icon: 'list',
  },
  {
    to: '/weights',
    label: '權重查詢',
    description: '依 ETF 查詢成分股權重',
    icon: 'chart',
  },
  {
    to: '/about',
    label: '關於本站',
    description: '隨機選股的學術依據與設計理念',
    icon: 'about',
  },
  {
    to: '/faq',
    label: '常見問題',
    description: '使用、資料與投資觀念 FAQ',
    icon: 'faq',
  },
]

const open = ref(false)
const route = useRoute()

function toggle(): void {
  open.value = !open.value
}

function close_menu(): void {
  open.value = false
}

function on_keydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && open.value) close_menu()
}

onMounted(() => {
  window.addEventListener('keydown', on_keydown)
})
onUnmounted(() => {
  window.removeEventListener('keydown', on_keydown)
})

// 路由變更時自動收合
watch(
  () => route.path,
  () => {
    open.value = false
  },
)
</script>

<template>
  <div class="app-menu">
    <button
      type="button"
      class="menu-btn"
      :class="{ 'is-open': open }"
      aria-label="開啟導覽選單"
      :aria-expanded="open"
      @click="toggle"
    >
      <span class="bar bar-1" />
      <span class="bar bar-2" />
      <span class="bar bar-3" />
    </button>

    <Transition name="overlay">
      <div
        v-if="open"
        class="overlay"
        aria-hidden="true"
        @click="close_menu"
      />
    </Transition>

    <Transition name="dropdown">
      <nav
        v-if="open"
        class="dropdown"
        role="menu"
        aria-label="導覽選單"
      >
        <span class="brand">DestinyOrder</span>
        <ul>
          <li v-for="item in NAV_ITEMS" :key="item.to">
            <RouterLink
              :to="item.to"
              class="item"
              :class="{ 'is-active': route.path === item.to }"
              role="menuitem"
            >
              <span class="item-icon" :class="`icon-${item.icon}`" aria-hidden="true">
                <DiceIcon v-if="item.icon === 'dice'" variant="outline" />
                <SlotIcon v-else-if="item.icon === 'slot'" />
              </span>
              <span class="item-text">
                <span class="item-label">{{ item.label }}</span>
                <span class="item-desc">{{ item.description }}</span>
              </span>
              <span class="item-arrow" aria-hidden="true">›</span>
            </RouterLink>
          </li>
        </ul>
      </nav>
    </Transition>
  </div>
</template>

<style scoped>
.app-menu {
  position: fixed;
  top: clamp(0.8rem, 2.5vw, 1.4rem);
  left: clamp(0.8rem, 2.5vw, 1.4rem);
  z-index: 60;
}

/* ---------- 漢堡按鈕 ---------- */

.menu-btn {
  position: relative;
  z-index: 2;
  width: 44px;
  height: 44px;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
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
    transform 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}
.menu-btn:hover {
  background: rgba(126, 200, 255, 0.2);
  border-color: rgba(179, 184, 255, 0.45);
}
.menu-btn:active {
  transform: scale(0.94);
}
.menu-btn.is-open {
  background: linear-gradient(135deg, #b3b8ff 0%, #7ec8ff 100%);
  border-color: transparent;
  color: #0b0f24;
}
.bar {
  width: 18px;
  height: 2px;
  background: currentColor;
  border-radius: 2px;
  transition:
    transform 0.32s cubic-bezier(0.4, 0.1, 0.3, 1.4),
    opacity 0.2s ease;
}
.menu-btn.is-open .bar-1 {
  transform: translateY(7px) rotate(45deg);
}
.menu-btn.is-open .bar-2 {
  opacity: 0;
  transform: scaleX(0.3);
}
.menu-btn.is-open .bar-3 {
  transform: translateY(-7px) rotate(-45deg);
}

/* ---------- 點擊背景關閉用透明 overlay ---------- */

.overlay {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: transparent;
}
.overlay-enter-active,
.overlay-leave-active {
  transition: opacity 0.2s ease;
}
.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}

/* ---------- 下拉選單 ---------- */

.dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  z-index: 1;
  min-width: 260px;
  padding: 0.6rem;
  border-radius: 16px;
  background:
    linear-gradient(
      180deg,
      rgba(20, 24, 48, 0.95) 0%,
      rgba(10, 12, 28, 0.96) 100%
    );
  border: 1px solid rgba(179, 184, 255, 0.18);
  box-shadow: 0 30px 60px -20px rgba(0, 0, 0, 0.7);
  color: #e8eaf6;
  font-family:
    'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif;
  transform-origin: top left;
}
.dropdown-enter-active,
.dropdown-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.28s cubic-bezier(0.22, 0.84, 0.32, 1);
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}

.brand {
  display: block;
  padding: 0.3rem 0.6rem 0.5rem;
  font-size: 0.66rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #8a8fae;
}

.dropdown ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 0.75rem;
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
  transition:
    background 0.2s ease,
    transform 0.15s ease;
  cursor: pointer;
}
.item:hover {
  background: rgba(255, 255, 255, 0.05);
}
.item:active {
  transform: scale(0.985);
}
.item.is-active {
  background: linear-gradient(
    135deg,
    rgba(126, 200, 255, 0.22),
    rgba(124, 92, 255, 0.22)
  );
  border: 1px solid rgba(179, 184, 255, 0.32);
  padding: calc(0.7rem - 1px) calc(0.75rem - 1px);
}

.item-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 1rem;
  flex-shrink: 0;
}

.item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.item-label {
  font-size: 0.92rem;
  font-weight: 700;
  color: #f0f2ff;
}
.item-desc {
  font-size: 0.74rem;
  color: #8a8fae;
}

.item-arrow {
  font-size: 1.2rem;
  color: #5e6285;
  transition:
    transform 0.2s ease,
    color 0.2s ease;
}

/* 海蓝色半透明图标 */
.item-icon.icon-list::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%235EC8FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>') center / contain no-repeat;
}
.item-icon.icon-chart::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%235EC8FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="19" x2="19" y2="19"/><polyline points="19 9 15 13 9 7 5 11"/></svg>') center / contain no-repeat;
}
.item-icon.icon-about::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%235EC8FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>') center / contain no-repeat;
}
.item-icon.icon-faq::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%235EC8FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/><circle cx="12" cy="12" r="10"/></svg>') center / contain no-repeat;
}
.item-icon.icon-list,
.item-icon.icon-chart,
.item-icon.icon-about,
.item-icon.icon-faq {
  position: relative;
  font-size: 0;
}
/* icon-slot 由 SlotIcon.vue 元件渲染（含 SVG + CSS 三軸滾動動畫），
   不再用 ::before 背景圖；保留 class 名稱僅為語意一致 */
.item-icon.icon-slot {
  font-size: 0;
}

.item:hover .item-arrow {
  transform: translateX(2px);
  color: #c9cce8;
}
.item.is-active .item-arrow {
  color: #b3b8ff;
}

/* ---------- RWD ---------- */

@media (max-width: 420px) {
  .dropdown {
    min-width: calc(100vw - 2rem);
  }
}

@media (prefers-reduced-motion: reduce) {
  .dropdown-enter-active,
  .dropdown-leave-active,
  .overlay-enter-active,
  .overlay-leave-active,
  .bar,
  .item-arrow {
    transition: none !important;
  }
}
</style>
