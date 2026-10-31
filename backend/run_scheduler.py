# -*- coding: utf-8-sig -*-
"""每日股價爬蟲排程器 CLI 入口。

用法（兩種啟動方式擇一，皆可）::

    # 1. 模組模式（建議，於專案根目錄執行）
    python -m backend.run_scheduler

    # 2. 直接執行（VS Code「執行檔案」按鈕也可）
    python backend/run_scheduler.py

啟動後立即執行一次完整爬蟲批次，之後常駐並於每日多個排定時刻
（見 ``backend.core.shared.config.DAILY_RUN_TIMES``）重新觸發。
同一天的多次執行會覆蓋同一個 ``yyyy/mm/dd`` 資料夾下的 JSON 檔。
按 Ctrl+C 可乾淨退出。
"""

import sys
from pathlib import Path

# 直接以檔案路徑執行（python backend/run_scheduler.py）時，sys.path[0]
# 會是 backend/ 而非專案根目錄，導致 `import backend.*` 失敗。
# 將專案根目錄補進 sys.path 以兼容兩種啟動方式；以 `python -m` 啟動時為無害冗餘。
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.funds.scheduler import run_forever  # noqa: E402
from backend.core.shared.log_handler import get_logger  # noqa: E402

logger = get_logger(__name__)


def main() -> None:
    """CLI 進入點。"""
    try:
        run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupted by user; scheduler exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
