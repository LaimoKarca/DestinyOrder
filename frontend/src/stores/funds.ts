import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DrawableStock } from '@/types/funds'
import { fetch_latest_funds } from '@/services/funds'

/**
 * 共用 funds 資料快取，讓 LuckyDraw 與 HoldingsView 共享同一份
 * `/api/funds/latest` payload，避免兩頁各自 fetch 重打 API。
 */
export const use_funds_store = defineStore('funds', () => {
  const stocks = ref<DrawableStock[]>([])
  const etf_codes = ref<string[]>([])
  const data_date = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loaded = ref(false)

  async function ensure_loaded(): Promise<void> {
    if (loaded.value || loading.value) return
    loading.value = true
    error.value = null
    try {
      const payload = await fetch_latest_funds()
      stocks.value = payload.stocks
      etf_codes.value = payload.etf_codes
      data_date.value = payload.date
      loaded.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function refresh(): Promise<void> {
    loaded.value = false
    await ensure_loaded()
  }

  return {
    stocks,
    etf_codes,
    data_date,
    loading,
    error,
    loaded,
    ensure_loaded,
    refresh,
  }
})
