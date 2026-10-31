# -*- coding: utf-8-sig -*-
"""TWSE 有價證券清單爬蟲排程器 CLI 入口。

用法（兩種啟動方式擇一，皆可）::

    # 1. 模組模式（建議，於專案根目錄執行）
    python -m backend.run_twse_securities

    # 2. 直接執行（VS Code「執行檔案」按鈕也可）
    python backend/run_twse_securities.py

啟動後立即執行一次完整擷取，之後常駐並於每日多個排定時刻
（見 ``backend.core.shared.config.TWSE_SECURITIES_RUN_TIMES``，預設 03:00 與 15:00）
重新觸發。輸出 ``backend/data/funds/symbol.json`` 與 ``backend/data/funds/symbol.csv``
皆採覆蓋寫入。按 Ctrl+C 可乾淨退出。
"""

import sys
from pathlib import Path

# 直接以檔案路徑執行（python backend/run_twse_securities.py）時，sys.path[0]
# 會是 backend/ 而非專案根目錄，導致 `import backend.*` 失敗。
# 將專案根目錄補進 sys.path 以兼容兩種啟動方式；以 `python -m` 啟動時為無害冗餘。
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.funds.twse_securities import run_forever  # noqa: E402
from backend.core.shared.log_handler import get_logger  # noqa: E402

logger = get_logger(__name__)


def main() -> None:
    """CLI 進入點。"""
    try:
        run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupted by user; TWSE securities scheduler exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
