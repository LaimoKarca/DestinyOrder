# -*- coding: utf-8-sig -*-
"""單一爬蟲獨立執行 helper（單元測試 / 偵錯 / 維護用）。

供各 crawler 檔尾的 ``if __name__ == "__main__":`` 區塊呼叫，將擷取結果
以 JSON 形式列印到 **stdout**；log 一律走 stderr，便於用 ``>`` 重導向只保
留資料而不混入 log。

範例（PowerShell）::

    python -m backend.core.funds.crawlers.yuanta_0050
    python -m backend.core.funds.crawlers.yuanta_0050 > out.json
"""

import json
import sys
from typing import Callable

from backend.schemas.stock_price import StockPriceSnapshot


def run_crawler_standalone(
    fetch_fn: Callable[[], StockPriceSnapshot | None],
    label: str,
) -> None:
    """執行單一 :func:`fetch` 並列印結果到 stdout。

    Args:
        fetch_fn: 該爬蟲模組的 :func:`fetch` 函式。
        label: 顯示用標籤，通常為基金代碼。

    Side Effects:
        成功時將 ``snapshot.model_dump()`` 以 4-space indent JSON 寫入 stdout。
        失敗時印出錯誤訊息至 stderr 並以 exit code 1 結束。
    """
    snapshot = fetch_fn()
    if snapshot is None:
        print(f"[ERROR] crawler {label} returned no data", file=sys.stderr)
        raise SystemExit(1)
    json.dump(
        snapshot.model_dump(),
        sys.stdout,
        ensure_ascii=False,
        indent=4,
    )
    sys.stdout.write("\n")
