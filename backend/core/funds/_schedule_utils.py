# -*- coding: utf-8-sig -*-
"""排程器共用工具：依「每日固定時刻清單」計算下一次觸發時間。

供 :mod:`backend.core.funds.scheduler` 與
:mod:`backend.core.funds.twse_securities` 等多時刻排程器共用。
"""

from datetime import datetime, timedelta


def seconds_until_next_run(
    times: tuple[tuple[int, int], ...],
    now: datetime | None = None,
) -> float:
    """計算距離下一次排定觸發時刻的等待秒數。

    Args:
        times: 每日觸發時刻清單，每筆為 ``(hour, minute)``。重複值會被
            自動去重；時序由本函式自行排序。``(0, 0)`` 同時代表「今日
            00:00」與「24:00」——當所有時刻皆已過，會自然遞延到隔日。
        now: 指定的「現在」時間；未提供則使用系統當下時間。

    Returns:
        距離 ``times`` 中下一個尚未到達的時刻的秒數；若今日所有時刻
        皆已過，回傳距隔日最早時刻的秒數。
    """
    moment = now or datetime.now()
    sorted_times = sorted(set(times))

    future_today = [
        moment.replace(hour=hour, minute=minute, second=0, microsecond=0)
        for hour, minute in sorted_times
        if moment.replace(hour=hour, minute=minute, second=0, microsecond=0) > moment
    ]
    if future_today:
        target = min(future_today)
    else:
        first_hour, first_minute = sorted_times[0]
        target = (moment + timedelta(days=1)).replace(
            hour=first_hour,
            minute=first_minute,
            second=0,
            microsecond=0,
        )
    return (target - moment).total_seconds()


def format_times(times: tuple[tuple[int, int], ...]) -> str:
    """將時刻清單轉成 ``"HH:MM, HH:MM, ..."`` 字串以利日誌輸出。"""
    return ", ".join(
        f"{hour:02d}:{minute:02d}" for hour, minute in sorted(set(times))
    )
