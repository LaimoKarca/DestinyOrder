# -*- coding: utf-8-sig -*-
"""統一投信 主動統一台股增長（00981A）爬蟲。

來源：ezmoney.com.tw fundCode=49YTW。此檔需先觸發 ``ShowStopList()``
展開全部持股列，再透過 ``#assetBody`` 容器內的表格擷取每一列。
"""

from typing import Final

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from backend.core.funds.crawlers._uni_helpers import (
    extract_date_from_label,
    extract_nav_from_value_tab,
)
from backend.core.shared.log_handler import get_logger
from backend.core.shared.playwright_helpers import headless_page
from backend.core.shared.text_cleaning import format_weight
from backend.schemas.stock_price import Holding, StockPriceSnapshot

logger = get_logger(__name__)

CODE: Final[str] = "00981A"
NAME: Final[str] = "主動統一台股增長"
URL: Final[str] = (
    "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=49YTW&tabName=basic#"
)

_HOLDINGS_TABLE_FEATURES: Final[tuple[str, ...]] = (
    "#assetBody table",  # filter applied later
    "#assetBody > table:nth-child(5)",
)
_NAME_HEADER_TOKENS: Final[frozenset[str]] = frozenset({"名稱", "型態", "品名"})


def _expand_all_holdings(page: Page) -> None:
    """透過原生 JavaScript 觸發「展開全部」功能。"""
    try:
        page.evaluate(
            """
            try {
                if (typeof ShowStopList === 'function') {
                    ShowStopList();
                } else {
                    const btn = document.getElementById('ShowStopListButton');
                    if (btn) btn.click();
                }
            } catch (e) { }
            """
        )
        page.wait_for_timeout(2500)
    except Exception as exc:
        logger.warning("Expand holdings failed: %s", exc)


def _locate_holdings_table(page: Page):
    """依序以特徵 / 索引尋找持股表。"""
    primary = page.locator(_HOLDINGS_TABLE_FEATURES[0]).filter(has_text="名稱").first
    if primary.count() > 0:
        return primary
    fallback = page.locator(_HOLDINGS_TABLE_FEATURES[1]).first
    if fallback.count() > 0:
        return fallback
    return None


def _extract_holdings(page: Page) -> list[Holding]:
    """擷取展開後的持股表內容。"""
    table = _locate_holdings_table(page)
    if table is None:
        logger.warning("Cannot locate holdings table.")
        return []

    try:
        table.locator("tbody tr").first.wait_for(state="attached", timeout=5000)
    except PlaywrightTimeoutError:
        logger.warning("Holdings rows not attached.")
        return []

    holdings: list[Holding] = []
    rows = table.locator("tbody tr")
    for i in range(rows.count()):
        row = rows.nth(i)
        name_cell = row.locator("td:nth-child(2)")
        weight_cell = row.locator("td:nth-child(4)")
        if name_cell.count() == 0 or weight_cell.count() == 0:
            continue
        name_text = name_cell.text_content().strip()
        weight_text = weight_cell.text_content().strip()
        is_header = any(token in name_text for token in _NAME_HEADER_TOKENS)
        if not name_text or is_header:
            continue
        holdings.append(Holding(name=name_text, weight=format_weight(weight_text)))
    return holdings


def _switch_to_value_tab(page: Page) -> bool:
    """以原生 JS 點擊頁籤切換鈕，避免捲動卡死。"""
    try:
        page.evaluate(
            """
            const tab = document.querySelector("a[data-toggle='tab'][href='#value']");
            if (tab) tab.click();
            """
        )
        page.wait_for_timeout(2000)
        return True
    except Exception as exc:
        logger.warning("Switch tab failed: %s", exc)
        return False


def fetch() -> StockPriceSnapshot | None:
    """執行 00981A 爬蟲流程。"""
    with headless_page() as page:
        logger.info("Loading %s", URL)
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning("Page load timeout.")
            return None

        update_time = extract_date_from_label(page)
        _expand_all_holdings(page)
        holdings = _extract_holdings(page)

        if not _switch_to_value_tab(page):
            return StockPriceSnapshot(
                code=CODE,
                name=NAME,
                nav="未取得",
                change_percent="未取得",
                update_time=update_time,
                holdings=holdings,
            )

        nav_text, change_text = extract_nav_from_value_tab(page)

    return StockPriceSnapshot(
        code=CODE,
        name=NAME,
        nav=nav_text,
        change_percent=change_text,
        update_time=update_time,
        holdings=holdings,
    )


if __name__ == "__main__":
    # 單獨執行此爬蟲（偵錯 / 單元測試 / 維護用）。
    # 於專案根目錄 (DestinyOrder/) 執行：
    #     python -m backend.core.funds.crawlers.uni_00981a
    # JSON 結果輸出到 stdout、log 輸出到 stderr。
    from backend.core.funds._dev_runner import run_crawler_standalone

    run_crawler_standalone(fetch, CODE)
