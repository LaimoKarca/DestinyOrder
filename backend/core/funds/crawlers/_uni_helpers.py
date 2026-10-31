# -*- coding: utf-8-sig -*-
"""統一投信 ezmoney.com.tw 系列 ETF 共用解析邏輯。

00403A 與 00981A 兩檔基金共用同一個 ezmoney 平台，網頁結構幾乎一致，
僅 fundCode 與持股表的展開方式不同。本模組集中兩者重複的：

* :func:`extract_date_from_label`：自帶有「資料日期」字樣的節點萃取日期
* :func:`extract_nav_from_value_tab`：自 ``#value`` 容器表格擷取淨值 / 漲跌幅，
  失敗時自動退回備援 XPath
"""

from typing import Final

from playwright.sync_api import Page

from backend.core.shared.log_handler import get_logger
from backend.core.shared.text_cleaning import (
    extract_date_or_today,
    extract_numeric,
    normalize_change_percent,
)

logger = get_logger(__name__)

_XPATH_NAV_FALLBACK: Final[str] = (
    "/html/body/div[1]/div/div[2]/div[7]/div[2]/div/div[4]/div[2]/div[2]/table"
    "/tbody/tr[2]/td[2]"
)
_XPATH_CHANGE_FALLBACK: Final[str] = (
    "/html/body/div[1]/div/div[2]/div[7]/div[2]/div/div[4]/div[2]/div[2]/table"
    "/tbody/tr[2]/td[4]"
)
_INVALID: Final[str] = "未取得"


def extract_date_from_label(page: Page) -> str:
    """從含有「資料日期」字樣的節點萃取 ``YYYY/MM/DD``，失敗時回今日日期。"""
    try:
        node = page.locator("*:has-text('資料日期')").last
        if node.count() > 0:
            return extract_date_or_today(node.text_content() or "")
    except Exception as exc:
        logger.warning("Extract date label failed: %s", exc)
    return extract_date_or_today("")


def _try_value_tab_primary(page: Page) -> tuple[str, str] | None:
    """優先路徑：透過 ``#value`` 容器內的第一個表格擷取。"""
    try:
        value_table = page.locator("#value table").first
        if value_table.count() == 0:
            return None
        rows = value_table.locator("tr")
        if rows.count() < 2:
            return None
        cells = rows.nth(1).locator("td")
        if cells.count() < 4:
            return None
        nav = extract_numeric(cells.nth(1).text_content().strip())
        change = normalize_change_percent(
            cells.nth(3).text_content().strip(),
            ensure_percent_suffix=True,
        )
        return nav, change
    except Exception as exc:
        logger.warning("Primary #value parse failed: %s", exc)
        return None


def _try_value_tab_fallback(page: Page) -> tuple[str, str]:
    """備援路徑：以絕對 XPath 擷取。"""
    nav = _INVALID
    change = _INVALID
    try:
        nav_elem = page.locator(f"xpath={_XPATH_NAV_FALLBACK}").first
        if nav_elem.count() > 0:
            nav = extract_numeric(nav_elem.text_content().strip())
        change_elem = page.locator(f"xpath={_XPATH_CHANGE_FALLBACK}").first
        if change_elem.count() > 0:
            change = normalize_change_percent(
                change_elem.text_content().strip(),
                ensure_percent_suffix=True,
            )
    except Exception as exc:
        logger.warning("XPath fallback failed: %s", exc)
    return nav, change


def extract_nav_from_value_tab(page: Page) -> tuple[str, str]:
    """切換至 ``#value`` 後擷取淨值與漲跌幅，附備援 XPath。"""
    primary = _try_value_tab_primary(page)
    if primary is not None:
        return primary
    return _try_value_tab_fallback(page)
