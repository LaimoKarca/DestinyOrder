import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const BGM_VOLUME = 0.4

/**
 * 全站共用的音訊狀態：
 * - `muted`：是否靜音。每次載入頁面都預設為「未靜音」，不 persist。
 * - BGM：常駐循環播放的背景音樂。
 * - SFX：拉霸機式 tick 與結算 ding，使用 Web Audio API 合成，免額外資源。
 */
export const use_audio_store = defineStore('audio', () => {
  const muted = ref<boolean>(false)
  let _bgm: HTMLAudioElement | null = null
  let _ctx: AudioContext | null = null

  function _ensure_ctx(): AudioContext | null {
    if (typeof window === 'undefined') return null
    try {
      const Ctor =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext
      if (!Ctor) return null
      _ctx ??= new Ctor()
      // 部分瀏覽器的 AudioContext 會處於 suspended，需要使用者互動後才恢復
      if (_ctx.state === 'suspended') {
        _ctx.resume().catch(() => {
          // 忽略 — 在下次互動時自然恢復
        })
      }
      return _ctx
    } catch {
      return null
    }
  }

  function init_bgm(src: string): void {
    if (_bgm || typeof window === 'undefined') return
    _bgm = new Audio(src)
    _bgm.loop = true
    _bgm.volume = BGM_VOLUME
    _bgm.preload = 'auto'
    _bgm.muted = muted.value

    _try_play_bgm()

    // 瀏覽器 autoplay policy 多半會擋住首次自動播放，等首次互動再嘗試
    const on_first_interaction = (): void => {
      _try_play_bgm()
      window.removeEventListener('pointerdown', on_first_interaction)
      window.removeEventListener('keydown', on_first_interaction)
    }
    window.addEventListener('pointerdown', on_first_interaction, { once: true })
    window.addEventListener('keydown', on_first_interaction, { once: true })
  }

  function _try_play_bgm(): void {
    if (!_bgm) return
    _bgm.muted = muted.value
    _bgm.play().catch(() => {
      // autoplay 被擋，等下次互動再試
    })
  }

  function toggle_muted(): void {
    // 如果使用者「第一次互動」就點喇叭按鈕，此時 BGM 還因 autoplay 被擋而 paused。
    // 此時點擊應視為「啟動 BGM」而非「切換靜音」，
    // 否則使用者會看到圖示變成靜音、又得再點第二下才聽得到聲音。
    if (_bgm && _bgm.paused) {
      muted.value = false
      _try_play_bgm()
      return
    }
    muted.value = !muted.value
  }

  watch(muted, (next) => {
    if (_bgm) {
      _bgm.muted = next
      if (!next) _try_play_bgm()
    }
  })

  /** 拉霸機式 tick：抽抽樂滾動時逐次跳動，短促清脆 */
  function play_tick(): void {
    if (muted.value) return
    const ctx = _ensure_ctx()
    if (!ctx) return
    try {
      const now = ctx.currentTime
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'square'
      osc.frequency.setValueAtTime(1500, now)
      osc.frequency.exponentialRampToValueAtTime(1900, now + 0.012)
      gain.gain.setValueAtTime(0.0001, now)
      gain.gain.exponentialRampToValueAtTime(0.14, now + 0.002)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.035)
      osc.connect(gain).connect(ctx.destination)
      osc.start(now)
      osc.stop(now + 0.05)
    } catch {
      // ignore
    }
  }

  /** 結算 ding：明亮鈴聲，三層泛音疊加營造金屬鐺感 */
  function play_ding(): void {
    if (muted.value) return
    const ctx = _ensure_ctx()
    if (!ctx) return
    try {
      const now = ctx.currentTime
      const master = ctx.createGain()
      master.gain.setValueAtTime(0.55, now)
      master.connect(ctx.destination)
      const layers: Array<{ freq: number; amp: number; decay: number }> = [
        { freq: 1760, amp: 0.35, decay: 1.1 },
        { freq: 2637, amp: 0.18, decay: 0.85 },
        { freq: 3520, amp: 0.09, decay: 0.6 },
      ]
      for (const { freq, amp, decay } of layers) {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.type = 'sine'
        osc.frequency.setValueAtTime(freq, now)
        gain.gain.setValueAtTime(0.0001, now)
        gain.gain.exponentialRampToValueAtTime(amp, now + 0.004)
        gain.gain.exponentialRampToValueAtTime(0.0001, now + decay)
        osc.connect(gain).connect(master)
        osc.start(now)
        osc.stop(now + decay + 0.05)
      }
    } catch {
      // ignore
    }
  }

  return {
    muted,
    init_bgm,
    toggle_muted,
    play_tick,
    play_ding,
  }
})
