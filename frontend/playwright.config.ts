import recoveryConfig from './playwright.recovery.config'

/**
 * 預設 Playwright 設定檔直接對齊已驗證之本機端對端測試設定 (`playwright.recovery.config.ts`)，
 * 讓 `npm run test:e2e` 與 `--config playwright.recovery.config.ts` 執行同一套驗證。
 */
export default recoveryConfig
