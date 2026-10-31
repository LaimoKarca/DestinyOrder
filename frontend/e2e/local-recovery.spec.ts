/* eslint-disable playwright/no-conditional-in-test, playwright/no-conditional-expect */
import { promises as fs } from 'node:fs'
import { dirname, resolve } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const EVIDENCE_DIR = resolve(__dirname, '..', 'test-results', 'recovery')
const EVIDENCE_FILE = resolve(EVIDENCE_DIR, 'recovery-evidence.json')
const E2E_BASE_URL =
  process.env.E2E_BASE_URL?.trim() || 'http://127.0.0.1:5173'

interface DrawSource {
  etf_code: string
  etf_name: string
  weight: string
}

interface DrawableStock {
  name: string
  symbol: string | null
  industry: string | null
  sources: DrawSource[]
}

interface FundsLuckyResponse {
  date: string
  etf_codes: string[]
  stocks: DrawableStock[]
}

interface EtfHolding {
  name: string
  symbol: string | null
  weight: string
}

interface EtfDetail {
  code: string
  name: string
  update_time: string
  source_url: string
  holdings: EtfHolding[]
}

interface FundsByEtfResponse {
  date: string
  etfs: EtfDetail[]
}

interface RuntimeTelemetry {
  consoleErrors: string[]
  consoleWarnings: string[]
  pageErrors: string[]
  blockedExternalUrls: string[]
  appFailedRequests: string[]
}

function isExternalBlockedUrl(urlStr: string): boolean {
  try {
    const parsed = new URL(urlStr)
    if (parsed.protocol === 'data:' || parsed.protocol === 'blob:') return false
    return parsed.hostname !== '127.0.0.1' && parsed.hostname !== 'localhost'
  } catch {
    return false
  }
}

async function setupPageTelemetryAndNetworkGuard(
  page: Page,
): Promise<RuntimeTelemetry> {
  const telemetry: RuntimeTelemetry = {
    consoleErrors: [],
    consoleWarnings: [],
    pageErrors: [],
    blockedExternalUrls: [],
    appFailedRequests: [],
  }

  await page.route('**/*', async (route) => {
    const req = route.request()
    const url = req.url()
    if (isExternalBlockedUrl(url)) {
      telemetry.blockedExternalUrls.push(url)
      await route.abort('blockedbyclient')
      return
    }
    await route.continue()
  })

  page.on('console', (msg) => {
    const text = msg.text()
    if (msg.type() === 'error') {
      // 區分因攔截外部廣告資源產生的網路載入提示與應用程式本身錯誤
      if (isExternalBlockedUrl(text) || text.includes('ERR_BLOCKED_BY_CLIENT')) {
        return
      }
      telemetry.consoleErrors.push(text)
    } else if (msg.type() === 'warning') {
      telemetry.consoleWarnings.push(text)
    }
  })

  page.on('pageerror', (err) => {
    telemetry.pageErrors.push(err.stack || err.message || String(err))
  })

  page.on('requestfailed', (req) => {
    const url = req.url()
    if (isExternalBlockedUrl(url)) return
    const failure = req.failure()?.errorText ?? 'unknown'
    // 僅忽略背景音訊媒體檔在無聲環境下的瀏覽器取消，絕不忽略本機 API / 腳本請求錯誤
    if (failure.includes('ERR_ABORTED') && req.resourceType() === 'media') {
      return
    }
    telemetry.appFailedRequests.push(`${req.method()} ${url} -> ${failure}`)
  })

  return telemetry
}

test.describe('DestinyOrder Local Recovery E2E Suite', () => {
  const summaryEvidence: Record<string, unknown> = {
    executedAt: new Date().toISOString(),
    baseURL: E2E_BASE_URL,
  }

  test.afterAll(async () => {
    await fs.mkdir(EVIDENCE_DIR, { recursive: true })
    await fs.writeFile(
      EVIDENCE_FILE,
      JSON.stringify(summaryEvidence, null, 2),
      'utf8',
    )
  })

  test('1. Vite Proxy API 驗證 (/api/health, /api/funds/latest, /api/funds/by_etf) 與六路由導覽', async ({
    page,
    request,
  }) => {
    const telemetry = await setupPageTelemetryAndNetworkGuard(page)

    // 1) 驗證 3 個後端 API 經由 Vite proxy (127.0.0.1:5173/api/*) 回傳實際 200 JSON
    const healthRes = await request.get('/api/health')
    expect(healthRes.status()).toBe(200)
    expect(healthRes.headers()['content-type']).toContain('application/json')
    const healthBody = (await healthRes.json()) as { status: string }
    expect(healthBody).toEqual({ status: 'ok' })

    const latestRes = await request.get('/api/funds/latest')
    expect(latestRes.status()).toBe(200)
    expect(latestRes.headers()['content-type']).toContain('application/json')
    const latestBody = (await latestRes.json()) as FundsLuckyResponse
    expect(latestBody.date).toMatch(/^\d{4}\/\d{2}\/\d{2}$/)
    expect(latestBody.etf_codes).toEqual([
      '0050',
      '006208',
      '009816',
      '00403A',
      '00981A',
    ])
    expect(latestBody.stocks.length).toBeGreaterThan(0)

    const byEtfRes = await request.get('/api/funds/by_etf')
    expect(byEtfRes.status()).toBe(200)
    expect(byEtfRes.headers()['content-type']).toContain('application/json')
    const byEtfBody = (await byEtfRes.json()) as FundsByEtfResponse
    expect(byEtfBody.date).toBe(latestBody.date)
    expect(byEtfBody.etfs.map((e) => e.code)).toEqual([
      '0050',
      '006208',
      '009816',
      '00403A',
      '00981A',
    ])

    // 2) 驗證 6 條前端路由皆回傳 HTTP 200、完成對應 API 載入並渲染實際資料元件
    const routeExpectations: Array<{
      path: string
      h1: string
      titlePart: string
      apiPath: string | null
      readySelector: string
    }> = [
      {
        path: '/',
        h1: '台股 ETF 抽抽樂',
        titlePart: '台股 ETF 命定抽抽樂',
        apiPath: '/api/funds/latest',
        readySelector: 'button.draw-btn',
      },
      {
        path: '/slot',
        h1: '台股 ETF 拉霸機',
        titlePart: '命定拉霸機',
        apiPath: '/api/funds/latest',
        readySelector: 'button.lever-btn',
      },
      {
        path: '/holdings',
        h1: '五檔 ETF 持股表',
        titlePart: '成分股一覽',
        apiPath: '/api/funds/latest',
        readySelector: 'tbody tr',
      },
      {
        path: '/weights',
        h1: '成分股權重查詢',
        titlePart: '權重查詢',
        apiPath: '/api/funds/by_etf',
        readySelector: 'tbody tr',
      },
      {
        path: '/about',
        h1: '為什麼我們需要一個',
        titlePart: '關於本站',
        apiPath: null,
        readySelector: 'article.about-article',
      },
      {
        path: '/faq',
        h1: '關於 DestinyOrder',
        titlePart: '常見問題 FAQ',
        apiPath: null,
        readySelector: 'h1',
      },
    ]

    const routeResults: Array<Record<string, unknown>> = []
    for (const item of routeExpectations) {
      const apiResponsePromise = item.apiPath
        ? page.waitForResponse(
            (res) =>
              res.url().includes(item.apiPath!) &&
              res.request().method() === 'GET' &&
              res.status() === 200,
          )
        : null

      const resp = await page.goto(item.path, { waitUntil: 'domcontentloaded' })
      expect(resp?.status()).toBe(200)

      if (apiResponsePromise) {
        const apiRes = await apiResponsePromise
        await apiRes.json()
        await expect(page.locator('.state-loading')).toHaveCount(0)
      }

      await expect(page.locator('h1').first()).toContainText(item.h1)
      await expect(page.locator(item.readySelector).first()).toBeVisible()
      await expect(page).toHaveTitle(new RegExp(item.titlePart))
      await expect(
        page.locator('ins[class*="adsby"], aside.banner-ad-slot, aside.side-ad'),
      ).toHaveCount(0)

      routeResults.push({
        path: item.path,
        status: resp?.status(),
        title: await page.title(),
        h1: (await page.locator('h1').first().textContent())?.trim(),
      })
    }

    expect(telemetry.pageErrors).toEqual([])
    expect(telemetry.consoleErrors).toEqual([])
    expect(telemetry.appFailedRequests).toEqual([])

    summaryEvidence.apiAndRoutes = {
      health: healthBody,
      latestDate: latestBody.date,
      latestStockCount: latestBody.stocks.length,
      byEtfCodes: byEtfBody.etfs.map((e) => ({
        code: e.code,
        holdingsCount: e.holdings.length,
        updateTime: e.update_time,
      })),
      routes: routeResults,
      telemetry,
    }
  })

  test('2. LuckyDraw (/)：空篩選 disabled 防呆、實際抽籤結果與後端股票池一致性', async ({
    page,
    request,
  }) => {
    const telemetry = await setupPageTelemetryAndNetworkGuard(page)
    const latestRes = await request.get('/api/funds/latest')
    const latestBody = (await latestRes.json()) as FundsLuckyResponse
    const poolByName = new Map(latestBody.stocks.map((s) => [s.name, s]))

    const apiLoaded = page.waitForResponse(
      (res) => res.url().includes('/api/funds/latest') && res.status() === 200,
    )
    await page.goto('/')
    await (await apiLoaded).json()

    const drawBtn = page.locator('button.draw-btn')
    await expect(drawBtn).toBeVisible()
    await expect(drawBtn).toBeEnabled()
    await expect(drawBtn).toContainText('開始抽抽')

    // 展開篩選下拉並取消勾選「全部」→ 驗證抽籤按鈕變成 disabled
    await page.locator('button.dropdown-toggle').click()
    const selectAllCheckbox = page
      .locator('.dropdown-menu label.dropdown-item')
      .first()
      .locator('input[type="checkbox"]')
    await expect(selectAllCheckbox).toBeChecked()
    await selectAllCheckbox.uncheck()
    await expect(drawBtn).toBeDisabled()

    // 重新勾選「全部」→ 驗證抽籤按鈕恢復 enabled
    await selectAllCheckbox.check()
    await expect(drawBtn).toBeEnabled()

    // 執行一次完整抽籤，等待 rolling (1.8s) + revealing (0.78s) 結束後驗證結果
    await drawBtn.click()
    await expect(page.locator('.card.has-result')).toBeVisible({
      timeout: 10_000,
    })
    await expect(drawBtn).toBeEnabled()
    await expect(drawBtn).toContainText('再抽一次')

    const drawnName = (
      await page.locator('.block-name').textContent()
    )?.trim()
    expect(drawnName).toBeTruthy()
    const matchedStock = poolByName.get(drawnName!)
    expect(matchedStock).toBeDefined()

    const metaVals = page.locator('.block-meta .meta-val')
    const drawnSymbol = (await metaVals.nth(0).textContent())?.trim()
    const drawnIndustry = (await metaVals.nth(1).textContent())?.trim()
    expect(drawnSymbol).toBe(matchedStock!.symbol ?? '——')
    expect(drawnIndustry).toBe(matchedStock!.industry ?? '未分類')

    const pillCodes = await page
      .locator('.card-sources .pill .pill-code')
      .allTextContents()
    const expectedCodes = matchedStock!.sources.map((s) => s.etf_code)
    expect([...pillCodes].sort()).toEqual([...expectedCodes].sort())

    expect(telemetry.pageErrors).toEqual([])
    expect(telemetry.consoleErrors).toEqual([])
    expect(telemetry.appFailedRequests).toEqual([])

    summaryEvidence.luckyDraw = {
      drawnName,
      drawnSymbol,
      drawnIndustry,
      pillCodes,
      telemetry,
    }
  })

  test('3. SlotMachine (/slot)：空篩選 disabled、拉桿至多 6 輪觸發保底命中與按鈕恢復', async ({
    page,
    request,
  }) => {
    const telemetry = await setupPageTelemetryAndNetworkGuard(page)
    const latestRes = await request.get('/api/funds/latest')
    const latestBody = (await latestRes.json()) as FundsLuckyResponse
    const poolByName = new Map(latestBody.stocks.map((s) => [s.name, s]))

    const apiLoaded = page.waitForResponse(
      (res) => res.url().includes('/api/funds/latest') && res.status() === 200,
    )
    await page.goto('/slot')
    await (await apiLoaded).json()

    const leverBtn = page.locator('button.lever-btn')
    await expect(leverBtn).toBeVisible()
    await expect(leverBtn).toBeEnabled()
    await expect(leverBtn).toContainText('拉動拉桿')

    // 驗證空篩選時拉桿 disabled
    await page.locator('button.dropdown-toggle').click()
    const selectAllCheckbox = page
      .locator('.dropdown-menu label.dropdown-item')
      .first()
      .locator('input[type="checkbox"]')
    await selectAllCheckbox.uncheck()
    await expect(leverBtn).toBeDisabled()
    await selectAllCheckbox.check()
    await expect(leverBtn).toBeEnabled()
    await page.locator('button.dropdown-toggle').click()

    // 拉霸保底閾值 PITY_THRESHOLD_MAX = 5，因此至多第 6 次拉桿必定命中 (force_win)
    const rounds: Array<{
      round: number
      outcome: 'win' | 'miss'
      centerNames: string[]
      buttonTextAfter: string
    }> = []
    let wonStockName: string | null = null

    for (let round = 1; round <= 6; round++) {
      await leverBtn.click()
      // 滾動約 3.1s，等待按鈕恢復 enabled 且所有三軸皆 settled
      await expect(leverBtn).toBeEnabled({ timeout: 15_000 })
      await expect(page.locator('.reel.is-settled')).toHaveCount(3)

      // 每一軸滾動條的倒數第二格 (nth-last-child(2)) 為停在視窗中線的標的
      const centerNames = await page
        .locator('.reel .reel-item:nth-last-child(2) .reel-name')
        .allTextContents()
      expect(centerNames).toHaveLength(3)

      const isWin = await page.locator('.result-area.has-result').isVisible()
      const isMiss = await page.locator('.result-area.is-miss').isVisible()
      expect(isWin || isMiss).toBe(true)

      const buttonTextAfter = (await leverBtn.textContent())?.trim() ?? ''
      rounds.push({
        round,
        outcome: isWin ? 'win' : 'miss',
        centerNames: centerNames.map((n) => n.trim()),
        buttonTextAfter,
      })

      if (isWin) {
        expect(centerNames[0]?.trim()).toBe(centerNames[1]?.trim())
        expect(centerNames[1]?.trim()).toBe(centerNames[2]?.trim())
        wonStockName = centerNames[0]!.trim()
        expect(poolByName.has(wonStockName)).toBe(true)
        expect(buttonTextAfter).toContain('再拉一次')
        break
      } else {
        expect(buttonTextAfter).toContain('不甘心，再拉！')
      }
    }

    expect(wonStockName).not.toBeNull()
    expect(telemetry.pageErrors).toEqual([])
    expect(telemetry.consoleErrors).toEqual([])
    expect(telemetry.appFailedRequests).toEqual([])

    summaryEvidence.slotMachine = {
      totalRoundsToWin: rounds.length,
      wonStockName,
      rounds,
      telemetry,
    }
  })

  test('4. HoldingsView (/holdings)：搜尋、產業別、ETF 篩選與清除還原驗證', async ({
    page,
    request,
  }) => {
    const telemetry = await setupPageTelemetryAndNetworkGuard(page)
    const latestRes = await request.get('/api/funds/latest')
    const latestBody = (await latestRes.json()) as FundsLuckyResponse
    const totalCount = latestBody.stocks.length

    const apiLoaded = page.waitForResponse(
      (res) => res.url().includes('/api/funds/latest') && res.status() === 200,
    )
    await page.goto('/holdings')
    await (await apiLoaded).json()

    const metaText = page.locator('.filter-meta .meta-text')
    await expect(metaText).toContainText(`${totalCount} / ${totalCount}`)
    await expect(page.locator('tbody tr')).toHaveCount(totalCount)

    // 1) 搜尋篩選：從實際 /api/funds/latest 動態挑選具代號、產業別且含 0050 來源之標的（不硬寫特定真實股票）
    const targetStock = latestBody.stocks.find(
      (s) =>
        Boolean(s.symbol) &&
        Boolean(s.industry) &&
        s.sources.some((src) => src.etf_code === '0050'),
    )
    expect(targetStock).toBeDefined()
    const targetSymbol = targetStock!.symbol!
    const targetIndustry = targetStock!.industry!
    const expectedSearchCount = latestBody.stocks.filter((s) => {
      const q = targetSymbol.toLowerCase()
      return (
        (s.symbol ?? '').toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q)
      )
    }).length

    const searchInput = page.locator('.filter-search input[type="search"]')
    await searchInput.fill(targetSymbol)
    await expect(page.locator('tbody tr')).toHaveCount(expectedSearchCount)
    await expect(page.locator('tbody tr').first()).toContainText(
      targetStock!.name,
    )

    // 2) 點擊「清除篩選」還原全部
    const clearBtn = page.locator('button.clear-inline')
    await expect(clearBtn).toBeVisible()
    await clearBtn.click()
    await expect(page.locator('tbody tr')).toHaveCount(totalCount)

    // 3) 產業別篩選：使用真實 locator.click() 選擇目標產業別
    const expectedIndustryCount = latestBody.stocks.filter(
      (s) => s.industry === targetIndustry,
    ).length
    const industryInput = page.locator('.filter-industry input[role="combobox"]')
    await industryInput.click()
    await page
      .locator('.filter-industry .combo-item', { hasText: targetIndustry })
      .first()
      .click()
    await expect(page.locator('tbody tr')).toHaveCount(expectedIndustryCount)

    // 4) 疊加 ETF 篩選：使用真實 locator.click() 選擇 0050
    const expectedIndustryAnd0050Count = latestBody.stocks.filter(
      (s) =>
        s.industry === targetIndustry &&
        s.sources.some((src) => src.etf_code === '0050'),
    ).length
    await page.locator('.filter-etf .combo-trigger').click()
    await page
      .locator('.filter-etf .combo-item-check', { hasText: '0050' })
      .first()
      .click()
    await expect(page.locator('tbody tr')).toHaveCount(
      expectedIndustryAnd0050Count,
    )
    // 收合 ETF 下拉選單，確保不遮擋後續按鈕點擊
    await page.locator('.filter-etf .combo-trigger').click()

    // 5) 再次點擊「清除篩選」驗證完全恢復
    await clearBtn.click()
    await expect(page.locator('tbody tr')).toHaveCount(totalCount)

    expect(telemetry.pageErrors).toEqual([])
    expect(telemetry.consoleErrors).toEqual([])
    expect(telemetry.appFailedRequests).toEqual([])

    summaryEvidence.holdingsView = {
      totalCount,
      targetSymbol,
      targetIndustry,
      expectedSearchCount,
      expectedIndustryCount,
      expectedIndustryAnd0050Count,
      telemetry,
    }
  })

  test('5. WeightsView (/weights)：切換五檔 ETF 並逐筆核對所有表格列與 /api/funds/by_etf 完全一致', async ({
    page,
    request,
  }) => {
    const telemetry = await setupPageTelemetryAndNetworkGuard(page)
    const byEtfRes = await request.get('/api/funds/by_etf')
    const byEtfBody = (await byEtfRes.json()) as FundsByEtfResponse

    const apiLoaded = page.waitForResponse(
      (res) => res.url().includes('/api/funds/by_etf') && res.status() === 200,
    )
    await page.goto('/weights')
    await (await apiLoaded).json()
    await expect(page.locator('.card')).toBeVisible()

    const checkedEtfs: Array<Record<string, unknown>> = []

    for (const etf of byEtfBody.etfs) {
      await page.locator('.meta-cell-select .combo-trigger').click()
      await page
        .locator('.meta-cell-select .combo-item', { hasText: etf.code })
        .first()
        .click()

      await expect(page.locator('.meta-cell-select .combo-display')).toHaveText(
        etf.code,
      )
      await expect(page.locator('.meta-cell-name .meta-value')).toHaveText(
        etf.name,
      )
      await expect(page.locator('.meta-cell-date .meta-value')).toHaveText(
        etf.update_time,
      )
      await expect(page.locator('a.source-link')).toHaveAttribute(
        'href',
        etf.source_url,
      )

      const rows = page.locator('tbody tr')
      await expect(rows).toHaveCount(etf.holdings.length)

      // 逐筆取出整張表格所有列，與後端 API 回傳之 holdings 陣列完整比對
      const actualHoldings = await rows.evaluateAll((trElements) =>
        trElements.map((tr) => {
          const cells = Array.from(tr.querySelectorAll('td')).map(
            (td) => td.textContent?.trim() ?? '',
          )
          return {
            symbol: cells[0] ?? '',
            name: cells[1] ?? '',
            weight: cells[2] ?? '',
          }
        }),
      )
      const expectedHoldings = etf.holdings.map((h) => ({
        symbol: h.symbol ?? '—',
        name: h.name,
        weight: h.weight,
      }))
      expect(actualHoldings).toEqual(expectedHoldings)

      checkedEtfs.push({
        code: etf.code,
        name: etf.name,
        updateTime: etf.update_time,
        holdingsCount: etf.holdings.length,
        allRowsVerified: true,
      })
    }

    expect(telemetry.pageErrors).toEqual([])
    expect(telemetry.consoleErrors).toEqual([])
    expect(telemetry.appFailedRequests).toEqual([])

    summaryEvidence.weightsView = {
      checkedEtfs,
      telemetry,
    }
  })
})
