import { test, expect } from '@playwright/test'

/**
 * 最小首頁載入煙霧測試（核心完整 E2E 驗證套件位於 `e2e/local-recovery.spec.ts`）。
 */
test('visits the app root url and renders main heading', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('h1')).toContainText('台股 ETF 抽抽樂')
})
