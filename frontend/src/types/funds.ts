export interface DrawSource {
  etf_code: string
  etf_name: string
  weight: string
}

export interface DrawableStock {
  name: string
  symbol: string | null
  industry: string | null
  sources: DrawSource[]
}

export interface FundsLuckyResponse {
  date: string
  etf_codes: string[]
  stocks: DrawableStock[]
}

/** 權重查詢 API：依 ETF 分組的單筆持股 */
export interface EtfHolding {
  name: string
  symbol: string | null
  weight: string
}

/** 權重查詢 API：單一 ETF 完整明細 */
export interface EtfDetail {
  code: string
  name: string
  update_time: string
  source_url: string
  holdings: EtfHolding[]
}

/** 權重查詢 API 回應 */
export interface FundsByEtfResponse {
  date: string
  etfs: EtfDetail[]
}
