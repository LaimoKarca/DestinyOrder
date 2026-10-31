import type {
  DrawableStock,
  FundsByEtfResponse,
  FundsLuckyResponse,
} from '@/types/funds'

async function _fetch_json<T>(url: string, fallback_msg: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  
  // 檢查 Content-Type（SEO & 穩定性防護）
  const contentType = res.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new Error(
      `無效的回應格式（期望 JSON，實際 ${contentType}）。請確認後端服務已啟動。`,
    )
  }

  if (!res.ok) {
    let detail = ''
    try {
      const body = (await res.json()) as { detail?: string }
      detail = body.detail ?? ''
    } catch {
      // ignore non-JSON error body
    }
    throw new Error(
      detail ? `${detail}（HTTP ${res.status}）` : `${fallback_msg} (HTTP ${res.status})`,
    )
  }

  try {
    return (await res.json()) as T
  } catch (e) {
    throw new Error(
      `JSON 解析失敗：${e instanceof Error ? e.message : '未知錯誤'}。請確認後端回應格式正確。`,
    )
  }
}

export async function fetch_latest_funds(): Promise<FundsLuckyResponse> {
  return _fetch_json<FundsLuckyResponse>('/api/funds/latest', '載入基金資料失敗')
}

export async function fetch_funds_by_etf(): Promise<FundsByEtfResponse> {
  return _fetch_json<FundsByEtfResponse>('/api/funds/by_etf', '載入 ETF 明細失敗')
}

export function pick_random_stock(pool: DrawableStock[]): DrawableStock {
  if (pool.length === 0) throw new Error('沒有可抽取的標的')
  const idx = Math.floor(Math.random() * pool.length)
  const picked = pool[idx]
  if (!picked) throw new Error('抽取失敗：索引超出範圍')
  return picked
}
