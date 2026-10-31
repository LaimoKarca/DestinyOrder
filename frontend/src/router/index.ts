import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import LuckyDraw from '@/views/LuckyDraw.vue'

const DEFAULT_SITE_ORIGIN = 'http://127.0.0.1:5173'
const SITE_URL_VALIDATION_ERROR =
  'Invalid VITE_SITE_URL: must be an http/https origin without credentials, path, query, or hash.'

export function normalize_site_url(raw?: string): string {
  const trimmed = raw?.trim() || DEFAULT_SITE_ORIGIN
  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  if (parsed.username !== '' || parsed.password !== '') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  if (parsed.search !== '' || parsed.hash !== '') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  if (parsed.pathname !== '/') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  return parsed.origin
}

const configured_site_url = (
  import.meta.env.VITE_SITE_URL as string | undefined
)?.trim()

function _resolve_site_origin(): string {
  if (configured_site_url) {
    try {
      return normalize_site_url(configured_site_url)
    } catch {
      // ignore invalid runtime override and fallback
    }
  }
  if (typeof window !== 'undefined' && window.location?.origin) {
    try {
      return normalize_site_url(window.location.origin)
    } catch {
      // fallback to default
    }
  }
  return DEFAULT_SITE_ORIGIN
}

/**
 * 為每條路由提供 SEO 必要欄位；router.afterEach 會把這些值寫進 document.head，
 * 讓 SPA 每頁都有獨立的 title、description 與 canonical。
 */
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    description?: string
    og_title?: string
    og_description?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'lucky-draw',
    component: LuckyDraw,
    meta: {
      title: 'DestinyOrder · 台股 ETF 命定抽抽樂｜成分股隨機抽選與權重查詢',
      description:
        '今天不知道要研究哪一檔？一鍵從 0050、006208、009816、00403A、00981A 等熱門 ETF 隨機抽選成分股，並查詢各檔權重佔比與產業分類。',
      og_title: 'DestinyOrder · 台股 ETF 命定抽抽樂',
      og_description:
        '今天不知道要研究哪檔？交給命定抽抽樂！一鍵隨機抽出熱門台股 ETF 成分股，並查詢各檔的 ETF 權重與產業分類。',
    },
  },
  {
    path: '/slot',
    name: 'slot-machine',
    // 路由懶載入：使用者不點 menu 就不會下載這支 chunk
    component: () => import('@/views/SlotMachine.vue'),
    meta: {
      title: '命定拉霸機｜台股 ETF 三軸選股博弈感體驗 · DestinyOrder',
      description:
        '想讓選股更刺激？命定拉霸機把 0050、006208、009816、00403A、00981A 五檔台股 ETF 成分股化作拉斯維加斯式拉霸三軸，三連中即定研究標的，搭配霓虹跑馬燈、JACKPOT 飛字與金幣雨特效，把選股變成沉浸式的命運博弈。',
      og_title: '命定拉霸機｜台股 ETF 三軸選股 · DestinyOrder',
      og_description:
        '把選股變成拉斯維加斯式的博弈！三軸同框、三連中即定，霓虹跑馬燈與金幣雨特效讓命運替你選股。',
    },
  },
  {
    path: '/holdings',
    name: 'holdings',
    // 路由懶載入：使用者不點 menu 就不會下載這支 chunk
    component: () => import('@/views/HoldingsView.vue'),
    meta: {
      title: '成分股一覽｜五檔台股 ETF 持股對照表 · DestinyOrder',
      description:
        '五檔熱門台股 ETF（0050、006208、009816、00403A、00981A）成分股對照表：支援代號 / 名稱搜尋、產業別與 ETF 多選篩選，並依「共同持有 ETF 筆數」自動排序，一眼看出哪檔台股被多檔 ETF 同時收錄。',
      og_title: '成分股一覽｜五檔台股 ETF 持股對照表',
      og_description:
        '五檔熱門台股 ETF 成分股對照表，支援搜尋與多重篩選，依「共同持有筆數」自動排序。',
    },
  },
  {
    path: '/weights',
    name: 'weights',
    component: () => import('@/views/WeightsView.vue'),
    meta: {
      title: '權重查詢｜依 ETF 查詢成分股權重佔比 · DestinyOrder',
      description:
        '依 ETF 代號（0050、006208、009816、00403A、00981A）查詢該檔基金的所有成分股與權重佔比，了解每檔台股 ETF 的持股結構與重點配置。',
      og_title: '權重查詢｜依 ETF 查詢成分股權重佔比',
      og_description:
        '依 ETF 代號查詢該檔基金的成分股與權重佔比，了解每檔台股 ETF 的持股結構。',
    },
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('@/views/AboutView.vue'),
    meta: {
      title: '關於本站｜隨機選股的學術依據與工具設計理念 · DestinyOrder',
      description:
        '為什麼要做一個隨機抽選台股 ETF 成分股的工具？從隨機漫步假說、效率市場假說、SPIVA 報告談起，深入探討「ETF 成分股自選」vs「直接持有 ETF」的方法論，以及拉斯維加斯式介面背後的行為經濟學設計哲學。',
      og_title: '關於 DestinyOrder｜隨機選股的學術依據',
      og_description:
        '隨機抽選有學術依據嗎？從漫步華爾街、效率市場假說到 SPIVA 報告，重新思考散戶選股的合理性。',
    },
  },
  {
    path: '/faq',
    name: 'faq',
    component: () => import('@/views/FaqView.vue'),
    meta: {
      title: '常見問題 FAQ｜DestinyOrder 使用、資料與投資觀念解答',
      description:
        'DestinyOrder 常見問題集合：隨機選股工具的用途、5 檔 ETF 為何選擇、權重資料更新頻率、主動式 ETF 含意、自選成分股 vs 直接買 ETF 的學術觀點，以及問題回饋與隱私政策。',
      og_title: '常見問題 FAQ · DestinyOrder',
      og_description:
        '關於 DestinyOrder 工具使用、學術依據、資料來源、隱私政策的完整解答。',
    },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// ---- Per-route SEO head updater ----
// 動態更新 document.title / meta description / canonical / og:* / twitter:*

function _upsert_meta_name(name: string, content: string): void {
  let el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('name', name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

function _upsert_meta_property(property: string, content: string): void {
  let el = document.querySelector<HTMLMetaElement>(`meta[property="${property}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('property', property)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

function _upsert_canonical(href: string): void {
  let el = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', 'canonical')
    document.head.appendChild(el)
  }
  el.setAttribute('href', href)
}

router.afterEach((to) => {
  if (typeof document === 'undefined') return

  const meta = to.meta
  const title = meta.title ?? document.title
  const description = meta.description
  const og_title = meta.og_title ?? title
  const og_description = meta.og_description ?? description
  const site_origin = _resolve_site_origin()
  const full_url = `${site_origin}${to.path}`

  document.title = title
  if (description) _upsert_meta_name('description', description)
  _upsert_canonical(full_url)

  _upsert_meta_property('og:title', og_title)
  if (og_description) _upsert_meta_property('og:description', og_description)
  _upsert_meta_property('og:url', full_url)

  _upsert_meta_name('twitter:title', og_title)
  if (og_description) _upsert_meta_name('twitter:description', og_description)
})

export default router
