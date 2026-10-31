# -*- coding: utf-8-sig -*-
"""文字清洗共用工具。

集中以下重複出現於各 crawler 的清洗邏輯：

* 移除括號 / 前後空白
* 漲跌幅字串正規化（補正負號、可選補百分比）
* 權重字串補百分比
* 從含日期的字串萃取 ``YYYY/MM/DD``
* 僅保留數字與小數點的數值清洗
* 判斷文字是否為擷取失敗的狀態提示詞
"""

import re
from datetime import datetime
from typing import Final

INVALID_TOKENS: Final[frozenset[str]] = frozenset({
    "未取得",
    "標籤內無文字",
    "等待元素逾時",
    "發生未預期錯誤",
})

_DATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\d{4}/\d{2}/\d{2}")


def is_invalid_token(value: str) -> bool:
    """判斷字串是否為空或屬於擷取失敗的狀態提示詞。"""
    return (not value) or value in INVALID_TOKENS


def strip_parentheses(text: str) -> str:
    """移除字串中的左右半形括號並去除前後空白。"""
    return text.replace("(", "").replace(")", "").strip()


def extract_numeric(text: str) -> str:
    """僅保留字串中的數字與小數點。

    Args:
        text: 原始字串。

    Returns:
        清理後的數值字串。範例：``"$ 187.25 元"`` -> ``"187.25"``。
    """
    return "".join(ch for ch in text if ch.isdigit() or ch == ".")


def normalize_change_percent(
    text: str,
    *,
    ensure_percent_suffix: bool = False,
) -> str:
    """正規化漲跌幅字串。

    依序執行：移除括號 -> 略過狀態提示詞 -> 補正號（若數值大於 0 且未帶
    正負號）-> 視旗標補上百分比符號。

    Args:
        text: 原始漲跌幅字串（可能帶括號、可能未帶正負號）。
        ensure_percent_suffix: 若為 True，確保字串以 ``%`` 結尾。

    Returns:
        正規化後的字串。若輸入為狀態提示詞則原樣回傳。
    """
    cleaned = strip_parentheses(text)
    if is_invalid_token(cleaned):
        return cleaned

    if not cleaned.startswith(("-", "+")):
        try:
            numeric_val = float(cleaned.replace("%", ""))
            if numeric_val > 0:
                cleaned = f"+{cleaned}"
        except ValueError:
            cleaned = f"+{cleaned}"

    if ensure_percent_suffix and not cleaned.endswith("%"):
        cleaned = f"{cleaned}%"

    return cleaned


def format_weight(text: str) -> str:
    """為權重字串補上百分比符號（若尚未具備）。

    狀態提示詞或空字串會原樣回傳。
    """
    cleaned = text.strip()
    if is_invalid_token(cleaned):
        return cleaned
    if not cleaned.endswith("%"):
        return f"{cleaned}%"
    return cleaned


def extract_date_or_today(text: str) -> str:
    """從含日期的字串中萃取 ``YYYY/MM/DD``，找不到時回傳今天日期。

    Args:
        text: 原始字串。例如 ``"資料日期：2026/05/21"``。

    Returns:
        ``YYYY/MM/DD`` 格式的日期字串。
    """
    match = _DATE_PATTERN.search(text or "")
    if match:
        return match.group()
    return datetime.now().strftime("%Y/%m/%d")
