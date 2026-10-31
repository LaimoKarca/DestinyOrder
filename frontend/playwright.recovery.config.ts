import process from 'node:process'
import { defineConfig, devices } from '@playwright/test'

const E2E_BASE_URL =
  process.env.E2E_BASE_URL?.trim() || 'http://127.0.0.1:5173'

/**
 * DestinyOrder 本機端對端驗證 Playwright 設定檔。
 * - 只使用現有 @playwright/test，不啟動內建 webServer（由外部先行啟動 FastAPI 與 Vite）
 * - 固定單一 worker、headless Chromium、baseURL 預設為 http://127.0.0.1:5173（可由 E2E_BASE_URL 覆寫）
 * - 測試證據與報告集中輸出至 test-results/recovery/
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: 'local-recovery.spec.ts',
  timeout: 90 * 1000,
  expect: {
    timeout: 10 * 1000,
  },
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  outputDir: './test-results/recovery/artifacts',
  reporter: [
    ['list'],
    ['json', { outputFile: './test-results/recovery/playwright-report.json' }],
  ],
  use: {
    baseURL: E2E_BASE_URL,
    headless: true,
    actionTimeout: 10 * 1000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: true,
      },
    },
  ],
})
