import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { Router } from 'vue-router'

import App from '../App.vue'
import appRouter, { normalize_site_url } from '@/router'
import { use_audio_store } from '@/stores/audio'
import LuckyDraw from '@/views/LuckyDraw.vue'
import SlotMachine from '@/views/SlotMachine.vue'
import HoldingsView from '@/views/HoldingsView.vue'
import WeightsView from '@/views/WeightsView.vue'
import AboutView from '@/views/AboutView.vue'
import FaqView from '@/views/FaqView.vue'
import type { FundsByEtfResponse, FundsLuckyResponse } from '@/types/funds'

const MOCK_LATEST_RESPONSE: FundsLuckyResponse = {
  date: '2026/05/24',
  etf_codes: ['0050', '006208', '009816', '00403A', '00981A'],
  stocks: [
    {
      name: '台積電',
      symbol: '2330',
      industry: '半導體業',
      sources: [
        { etf_code: '0050', etf_name: '元大台灣50', weight: '52.10%' },
        { etf_code: '006208', etf_name: '富邦台50', weight: '52.05%' },
      ],
    },
    {
      name: '鴻海',
      symbol: '2317',
      industry: '其他電子業',
      sources: [
        { etf_code: '0050', etf_name: '元大台灣50', weight: '4.80%' },
      ],
    },
  ],
}

const MOCK_BY_ETF_RESPONSE: FundsByEtfResponse = {
  date: '2026/05/24',
  etfs: [
    {
      code: '0050',
      name: '元大台灣50',
      update_time: '2026/05/24',
      source_url: 'https://www.yuantaetfs.com/product/detail/0050/ratio',
      holdings: [
        {
          name: '台積電',
          symbol: '2330',
          weight: '52.10%',
        },
        {
          name: '鴻海',
          symbol: '2317',
          weight: '4.80%',
        },
      ],
    },
  ],
}

function create_test_router(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'lucky-draw', component: LuckyDraw },
      { path: '/slot', name: 'slot-machine', component: SlotMachine },
      { path: '/holdings', name: 'holdings', component: HoldingsView },
      { path: '/weights', name: 'weights', component: WeightsView },
      { path: '/about', name: 'about', component: AboutView },
      { path: '/faq', name: 'faq', component: FaqView },
    ],
  })
}

describe('App', () => {
  let active_wrapper: VueWrapper | null = null
  let bgm_paused = true

  beforeEach(() => {
    bgm_paused = true

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi
        .fn<(query: string) => MediaQueryList>()
        .mockImplementation((query: string): MediaQueryList => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn<MediaQueryList['addListener']>(),
          removeListener: vi.fn<MediaQueryList['removeListener']>(),
          addEventListener: vi.fn<MediaQueryList['addEventListener']>(),
          removeEventListener: vi.fn<MediaQueryList['removeEventListener']>(),
          dispatchEvent: vi.fn<MediaQueryList['dispatchEvent']>(),
        })),
    })

    class MockResizeObserver {
      observe = vi.fn<ResizeObserver['observe']>()
      unobserve = vi.fn<ResizeObserver['unobserve']>()
      disconnect = vi.fn<ResizeObserver['disconnect']>()
    }
    vi.stubGlobal('ResizeObserver', MockResizeObserver)

    // use_dice_favicon 內建 null 保護，stub getContext 回傳 null 可避免 jsdom 未實作警告
    vi.spyOn(window.HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
      null,
    )

    Object.defineProperty(window.HTMLMediaElement.prototype, 'paused', {
      configurable: true,
      get: () => bgm_paused,
    })
    vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockResolvedValue(
      undefined,
    )
    vi.spyOn(window.HTMLMediaElement.prototype, 'pause').mockImplementation(
      () => {
        bgm_paused = true
      },
    )

    const fetch_mock = vi.fn<typeof fetch>(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()
      const payload = url.includes('/api/funds/by_etf')
        ? MOCK_BY_ETF_RESPONSE
        : MOCK_LATEST_RESPONSE
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    })
    vi.stubGlobal('fetch', fetch_mock)
  })

  afterEach(() => {
    if (active_wrapper) {
      active_wrapper.unmount()
      active_wrapper = null
    }
    document.documentElement.classList.remove('app-no-scroll')
    document.body.style.overflow = ''
    document.body.innerHTML = ''
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('mounts App at / (LuckyDraw) with real Pinia and Router, without ad slots, and renders GitHub Issues feedback link', async () => {
    const pinia = createPinia()
    const router = create_test_router()
    await router.push('/')
    await router.isReady()

    active_wrapper = mount(App, {
      global: {
        plugins: [pinia, router],
      },
    })
    await flushPromises()

    // Global shell components
    const menu_btn = active_wrapper.find('button[aria-label="開啟導覽選單"]')
    expect(menu_btn.exists()).toBe(true)
    expect(menu_btn.attributes('aria-expanded')).toBe('false')

    const speaker_btn = active_wrapper.find('button.speaker-btn')
    expect(speaker_btn.exists()).toBe(true)

    const footer = active_wrapper.find('footer.app-footer')
    expect(footer.exists()).toBe(true)
    expect(footer.text()).toContain('DestinyOrder')
    expect(footer.text()).toContain('投資免責條款')

    const contact_link = footer.find('a.contact-link')
    expect(contact_link.exists()).toBe(true)
    expect(contact_link.attributes('href')).toBe(
      'https://github.com/LaimoKarca/DestinyOrder/issues',
    )

    // Open-source build contains zero ad slots
    expect(active_wrapper.find('ins[class*="adsby"]').exists()).toBe(false)
    expect(active_wrapper.find('aside.banner-ad-slot').exists()).toBe(false)
    expect(active_wrapper.find('aside.side-ad').exists()).toBe(false)

    expect(active_wrapper.find('h1').text()).toBe('台股 ETF 抽抽樂')

    const draw_btn = active_wrapper.find('button.draw-btn')
    expect(draw_btn.exists()).toBe(true)
    expect(draw_btn.attributes('disabled')).toBeUndefined()
    expect(draw_btn.text()).toContain('開始抽抽')
  })

  it('opens AppMenu navigation, lists all 6 routes, and preserves /slot mobile scroll lock', async () => {
    const pinia = createPinia()
    const router = create_test_router()
    await router.push('/')
    await router.isReady()

    active_wrapper = mount(App, {
      global: {
        plugins: [pinia, router],
      },
    })
    await flushPromises()

    const menu_btn = active_wrapper.find('button[aria-label="開啟導覽選單"]')
    await menu_btn.trigger('click')
    expect(menu_btn.attributes('aria-expanded')).toBe('true')

    const nav = active_wrapper.find('nav[role="menu"]')
    expect(nav.exists()).toBe(true)

    const menu_items = nav.findAll('a[role="menuitem"]')
    expect(menu_items.map((item) => item.attributes('href'))).toEqual([
      '/',
      '/slot',
      '/holdings',
      '/weights',
      '/about',
      '/faq',
    ])

    // Navigate to a long-content route (/about)
    await router.push('/about')
    await flushPromises()

    // AppMenu auto-closes on route change
    expect(active_wrapper.find('nav[role="menu"]').exists()).toBe(false)
    expect(active_wrapper.find('h1').text()).toContain('隨機選股')
    expect(document.documentElement.classList.contains('app-no-scroll')).toBe(
      false,
    )

    // Navigate to /slot
    await router.push('/slot')
    await flushPromises()

    expect(active_wrapper.find('h1').text()).toContain('台股 ETF 拉霸機')
    expect(document.documentElement.classList.contains('app-no-scroll')).toBe(
      true,
    )
  })

  it('toggles synthesized audio mute by default, supports optional BGM autoplay recovery, and opens/closes disclaimer dialog', async () => {
    const pinia = createPinia()
    const router = create_test_router()
    await router.push('/')
    await router.isReady()

    active_wrapper = mount(App, {
      attachTo: document.body,
      global: {
        plugins: [pinia, router],
      },
    })
    await flushPromises()

    const speaker_btn = active_wrapper.find('button.speaker-btn')
    expect(speaker_btn.classes('is-muted')).toBe(false)
    expect(speaker_btn.attributes('aria-label')).toBe('靜音')

    // 1) 預設未設定 VITE_BGM_URL 時，點擊喇叭直接切換合成音效靜音狀態
    await speaker_btn.trigger('click')
    expect(speaker_btn.classes('is-muted')).toBe(true)
    expect(speaker_btn.attributes('aria-label')).toBe('取消靜音')

    await speaker_btn.trigger('click')
    expect(speaker_btn.classes('is-muted')).toBe(false)
    expect(speaker_btn.attributes('aria-label')).toBe('靜音')

    // 2) 若啟用選用 BGM 且因 autoplay 被擋處於 paused=true，首次點擊啟動播放，之後點擊切換靜音
    const audio_store = use_audio_store(pinia)
    audio_store.init_bgm('/custom-bgm.mp3')
    bgm_paused = true
    await speaker_btn.trigger('click')
    expect(speaker_btn.classes('is-muted')).toBe(false)

    bgm_paused = false
    await speaker_btn.trigger('click')
    expect(speaker_btn.classes('is-muted')).toBe(true)
    await speaker_btn.trigger('click')
    expect(speaker_btn.classes('is-muted')).toBe(false)

    // 3) AppFooter disclaimer modal (Teleported to body)
    const disclaimer_btn = active_wrapper.find('button.disclaimer-link')
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()

    await disclaimer_btn.trigger('click')
    await flushPromises()

    const dialog = document.body.querySelector('[role="dialog"]')
    expect(dialog).not.toBeNull()
    expect(dialog?.textContent).toContain('【免責聲明】')

    const confirm_btn = document.body.querySelector<HTMLButtonElement>(
      'button.modal-confirm',
    )
    expect(confirm_btn).not.toBeNull()
    confirm_btn?.click()
    await flushPromises()

    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
  })

  it('validates VITE_SITE_URL strictly as http/https origin and never echoes invalid input', () => {
    expect(normalize_site_url()).toBe('http://127.0.0.1:5173')
    expect(normalize_site_url('   ')).toBe('http://127.0.0.1:5173')
    expect(normalize_site_url('https://example.org/')).toBe(
      'https://example.org',
    )

    const maliciousInputs = [
      'ftp://example.org',
      'https://dummy_user:dummy_pass@example.org',
      'https://example.org/subpath',
      'https://example.org?x=1',
      'https://example.org#frag',
      'https://example.org"><script>alert(1)</script>',
    ]
    for (const bad of maliciousInputs) {
      let caught: Error | null = null
      try {
        normalize_site_url(bad)
      } catch (err) {
        caught = err as Error
      }
      expect(caught).not.toBeNull()
      expect(caught?.message).toBe(
        'Invalid VITE_SITE_URL: must be an http/https origin without credentials, path, query, or hash.',
      )
      expect(caught?.message).not.toContain(bad)
    }
  })

  it('injects normalized VITE_SITE_URL into client bundle and keeps canonical/og:url consistent across all 6 routes', async () => {
    const expectedOrigin = normalize_site_url(
      import.meta.env.VITE_SITE_URL as string | undefined,
    )
    expect(import.meta.env.VITE_SITE_URL).toBe(expectedOrigin)

    const routes = ['/', '/slot', '/holdings', '/weights', '/about', '/faq']
    for (const routePath of routes) {
      await appRouter.push(routePath)
      await appRouter.isReady()

      const canonical = document
        .querySelector<HTMLLinkElement>('link[rel="canonical"]')
        ?.getAttribute('href')
      const ogUrl = document
        .querySelector<HTMLMetaElement>('meta[property="og:url"]')
        ?.getAttribute('content')
      expect(canonical).toBe(`${expectedOrigin}${routePath}`)
      expect(ogUrl).toBe(`${expectedOrigin}${routePath}`)
    }
  })
})
