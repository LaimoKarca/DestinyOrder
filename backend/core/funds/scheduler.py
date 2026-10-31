# -*- coding: utf-8-sig -*-
"""每日多時刻觸發 orchestrator 的常駐排程器。

行為：

* 啟動時立即執行一次（不論輸出檔案是否已存在皆覆寫）
* 之後常駐，於 :data:`DAILY_RUN_TIMES` 列出的每個時刻重新執行
* 同一天的多次執行會寫入同一個 ``yyyy/mm/dd`` 資料夾，後者覆蓋前者
"""

import time
from datetime import datetime, timedelta

from backend.core.funds._schedule_utils import format_times, seconds_until_next_run
from backend.core.funds.orchestrator import run_all
from backend.core.shared.config import DAILY_RUN_TIMES
from backend.core.shared.log_handler import get_logger

logger = get_logger(__name__)


def run_forever() -> None:
    """常駐主迴圈：啟動立即執行，之後於每個排定時刻重新觸發。"""
    logger.info(
        "Scheduler starting. Daily triggers at %s.",
        format_times(DAILY_RUN_TIMES),
    )

    run_all()

    while True:
        wait_secs = seconds_until_next_run(DAILY_RUN_TIMES)
        next_at = datetime.now() + timedelta(seconds=wait_secs)
        logger.info(
            "Sleeping until next run: %s (in %.0fs)",
            next_at.strftime("%Y-%m-%d %H:%M:%S"),
            wait_secs,
        )
        time.sleep(wait_secs)
        run_all()
