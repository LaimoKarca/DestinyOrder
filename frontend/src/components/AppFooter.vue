<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'

const current_year = computed<number>(() => new Date().getFullYear())

const disclaimer_open = ref(false)
const dialog_ref = ref<HTMLElement | null>(null)
const trigger_ref = ref<HTMLButtonElement | null>(null)

function open_disclaimer(): void {
  disclaimer_open.value = true
}

function close_disclaimer(): void {
  disclaimer_open.value = false
}

// 開啟時鎖定 body scroll、聚焦對話框；關閉時還原並把焦點交還觸發按鈕。
// 只允許使用者透過「了解並關閉」按鈕關閉（不接受 Esc、不接受背景點擊）。
watch(disclaimer_open, async (open) => {
  if (open) {
    document.body.style.overflow = 'hidden'
    await Promise.resolve()
    dialog_ref.value?.focus()
  } else {
    document.body.style.overflow = ''
    trigger_ref.value?.focus()
  }
})

onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <footer class="app-footer" role="contentinfo">
    <div class="footer-inner">
      <span class="copy">
        Copyright © {{ current_year }}
        <span class="brand">DestinyOrder</span>
      </span>
      <span class="sep" aria-hidden="true">·</span>
      <span class="rights">All rights reserved.</span>
      <span class="sep" aria-hidden="true">·</span>
      <button
        ref="trigger_ref"
        type="button"
        class="disclaimer-link"
        aria-haspopup="dialog"
        :aria-expanded="disclaimer_open"
        @click="open_disclaimer"
      >
        投資免責條款
      </button>
      <span class="sep" aria-hidden="true">·</span>
      <a
        class="contact-link"
        href="https://github.com/LaimoKarca/DestinyOrder/issues"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="前往 GitHub Issues 回報問題"
      >問題回饋</a>
    </div>

    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="disclaimer_open"
          class="modal-backdrop"
          role="presentation"
        >
          <div
            ref="dialog_ref"
            class="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="disclaimer-title"
            tabindex="-1"
          >
            <header class="modal-header">
              <h2 id="disclaimer-title" class="modal-title">
                投資免責條款
              </h2>
            </header>

            <div class="modal-body">
              <h3 class="section-title">【免責聲明】</h3>
              <p>
                本網站提供之 ETF 成分股與權重資料，均由程式自動自官方來源抓取，僅供學術研究與參考用途，絕不構成任何形式之投資建議、推薦、買賣邀約或暗示。
              </p>
              <p>
                雖力求資料準確，但受限於官方更新時間差、系統延遲或技術限制，本網站不保證資訊之絕對即時性、正確性與完整性。金融市場具備高度波動風險，過去之績效不代表未來收益。任何投資決策皆須審慎評估，投資人應自行衡量風險承受能力，並自負最終投資盈虧之全責。因使用本網站資訊而產生之任何直接或間接損失，本網站及開發者概不承擔法律與財務責任。
              </p>
            </div>

            <footer class="modal-footer">
              <button
                type="button"
                class="modal-confirm"
                @click="close_disclaimer"
              >
                了解並關閉
              </button>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </footer>
</template>

<style scoped>
.app-footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 55;
  display: flex;
  justify-content: center;
  padding: 0.45rem 1rem calc(0.45rem + env(safe-area-inset-bottom, 0px));
  pointer-events: none;
  background: linear-gradient(
    180deg,
    rgba(7, 10, 26, 0) 0%,
    rgba(7, 10, 26, 0.78) 55%,
    rgba(7, 10, 26, 0.92) 100%
  );
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-top: 1px solid rgba(179, 184, 255, 0.08);
}

.footer-inner {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  flex-wrap: nowrap;
  justify-content: center;
  gap: 0.45rem;
  font-size: clamp(0.58rem, 1.85vw, 0.78rem);
  letter-spacing: 0.02em;
  color: #8a8fae;
  line-height: 1.4;
  text-align: center;
  white-space: nowrap;
  font-family:
    'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif;
}

.copy {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
  font-variant-numeric: tabular-nums;
}

.brand {
  font-weight: 700;
  background: linear-gradient(90deg, #b3b8ff 0%, #7ec8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  letter-spacing: 0.04em;
}

.sep {
  color: #4a4f73;
}

.rights {
  color: #6e7396;
}

/* ---------- Disclaimer link ---------- */

.disclaimer-link {
  padding: 0;
  margin: 0;
  background: transparent;
  border: 0;
  cursor: pointer;
  font: inherit;
  color: #b3b8ff;
  text-decoration: underline;
  text-decoration-color: rgba(179, 184, 255, 0.4);
  text-underline-offset: 3px;
  transition:
    color 0.2s ease,
    text-decoration-color 0.2s ease;
}
.disclaimer-link:hover,
.disclaimer-link:focus-visible {
  color: #fff;
  text-decoration-color: #fff;
  outline: none;
}

/* ---------- Contact link ---------- */

.contact-link {
  color: #b3b8ff;
  text-decoration: underline;
  text-decoration-color: rgba(179, 184, 255, 0.4);
  text-underline-offset: 3px;
  transition:
    color 0.2s ease,
    text-decoration-color 0.2s ease;
}
.contact-link:hover,
.contact-link:focus-visible {
  color: #fff;
  text-decoration-color: #fff;
  outline: none;
}

/* ---------- Modal ---------- */

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(1rem, 4vw, 2rem);
  background: rgba(5, 7, 18, 0.72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.modal {
  position: relative;
  width: min(560px, 100%);
  max-height: min(80dvh, 640px);
  display: flex;
  flex-direction: column;
  border-radius: clamp(14px, 2.4vw, 20px);
  background: linear-gradient(
    180deg,
    rgba(22, 26, 52, 0.98) 0%,
    rgba(10, 12, 28, 0.98) 100%
  );
  border: 1px solid rgba(179, 184, 255, 0.22);
  box-shadow:
    0 40px 80px -20px rgba(0, 0, 0, 0.7),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  color: #e8eaf6;
  font-family:
    'Inter', 'Noto Sans TC', system-ui, -apple-system, 'Segoe UI', sans-serif;
  outline: none;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem clamp(1rem, 3vw, 1.5rem) 0.85rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.modal-title {
  margin: 0;
  font-size: clamp(1rem, 3.4vw, 1.15rem);
  font-weight: 800;
  letter-spacing: 0.04em;
  text-align: center;
  background: linear-gradient(90deg, #fff 0%, #b3b8ff 60%, #7ec8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.modal-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.9rem clamp(1rem, 3vw, 1.5rem) 1rem;
  font-size: clamp(0.84rem, 2.6vw, 0.92rem);
  line-height: 1.75;
  color: #c9cce8;
}
.modal-body p {
  margin: 0 0 0.8rem;
}
.modal-body p:last-child {
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 0.6rem;
  font-size: clamp(0.86rem, 2.6vw, 0.95rem);
  font-weight: 700;
  color: #b3b8ff;
  letter-spacing: 0.04em;
}

.modal-footer {
  padding: 0.85rem clamp(1rem, 3vw, 1.5rem) 1.05rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  justify-content: center;
}

.modal-confirm {
  appearance: none;
  padding: 0.65rem 1.6rem;
  font-size: 0.92rem;
  font-weight: 700;
  font-family: inherit;
  color: #0b0f24;
  background: linear-gradient(135deg, #b3b8ff 0%, #7ec8ff 100%);
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  letter-spacing: 0.04em;
  transition:
    transform 0.18s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease;
  box-shadow: 0 12px 28px -10px rgba(124, 92, 255, 0.5);
}
.modal-confirm:hover,
.modal-confirm:focus-visible {
  filter: brightness(1.06);
  transform: translateY(-1px);
  outline: none;
  box-shadow: 0 16px 32px -10px rgba(124, 92, 255, 0.6);
}
.modal-confirm:active {
  transform: translateY(0);
  filter: brightness(0.96);
}

/* ---------- Transition ---------- */

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.22s ease;
}
.modal-enter-active .modal,
.modal-leave-active .modal {
  transition:
    opacity 0.22s ease,
    transform 0.28s cubic-bezier(0.22, 0.84, 0.32, 1);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal,
.modal-leave-to .modal {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}

/* ---------- RWD ---------- */

@media (max-width: 540px) {
  .footer-inner {
    gap: 0.3rem;
  }
  .copy {
    gap: 0.22rem;
  }
}

@media (max-width: 360px) {
  .footer-inner {
    font-size: 0.54rem;
    gap: 0.22rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .modal-enter-active,
  .modal-leave-active,
  .modal-enter-active .modal,
  .modal-leave-active .modal {
    transition: none !important;
  }
}
</style>
