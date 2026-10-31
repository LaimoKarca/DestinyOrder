# -*- coding: utf-8-sig -*-
"""統一投信 主動統一升級 50（00403A）爬蟲。

來源：ezmoney.com.tw fundCode=63YTW。基本資料頁讀取持股與資料日期，
切換至「淨值走勢」頁籤後讀取最新淨值與漲跌幅。
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

CODE: Final[str] = "00403A"
NAME: Final[str] = "主動統一升級50"
URL: Final[str] = (
    "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=63YTW&tabName=basic#"
)

_TAB_SELECTOR: Final[str] = "a[data-toggle='tab'][href='#value']"
_HOLDINGS_TABLE_FEATURES: Final[tuple[str, ...]] = (
    "table:has-text('名稱'):has-text('權重')",
    "table:has-text('品名'):has-text('比例')",
)
_NAME_HEADER_TOKENS: Final[frozenset[str]] = frozenset({"名稱", "型態"})
_FALLBACK_NAME_XPATH_TPL: Final[str] = (
    "/html/body/div[1]/div/div[2]/div[7]/div[2]/div/div[3]/div/div[2]/table[4]"
    "/tbody/tr[{idx}]/td[2]/span"
)
_FALLBACK_WEIGHT_XPATH_TPL: Final[str] = (
    "/html/body/div[1]/div/div[2]/div[7]/div[2]/div/div[3]/div/div[2]/table[4]"
    "/tbody/tr[{idx}]/td[4]/span"
)
_FALLBACK_ROW_START: Final[int] = 3
_FALLBACK_ROW_END: Final[int] = 52


def _locate_holdings_table(page: Page):
    """依序以特徵選擇器尋找持股表，找到即回傳；皆無回 None。"""
    for selector in _HOLDINGS_TABLE_FEATURES:
        target = page.locator(selector).first
        if target.count() > 0:
            return target
    return None


def _extract_holdings_primary(page: Page) -> list[Holding]:
    """優先路徑：以特徵定位持股表並讀取每一列。"""
    table = _locate_holdings_table(page)
    if table is None:
        return []

    try:
        table.locator("tr").first.wait_for(state="attached", timeout=5000)
    except PlaywrightTimeoutError:
        logger.warning("Holdings table rows not attached.")
        return []

    holdings: list[Holding] = []
    rows = table.locator("tr")
    for i in range(rows.count()):
        cells = rows.nth(i).locator("td")
        if cells.count() < 4:
            continue
        name_text = cells.nth(1).text_content().strip()
        weight_text = cells.nth(3).text_content().strip()
        is_header = any(token in name_text for token in _NAME_HEADER_TOKENS)
        if not name_text or is_header:
            continue
        holdings.append(Holding(name=name_text, weight=format_weight(weight_text)))
    return holdings


def _extract_holdings_fallback(page: Page) -> list[Holding]:
    """備援路徑：以絕對 XPath 擷取。"""
    holdings: list[Holding] = []
    for idx in range(_FALLBACK_ROW_START, _FALLBACK_ROW_END + 1):
        name_elem = page.locator(
            f"xpath={_FALLBACK_NAME_XPATH_TPL.format(idx=idx)}"
        )
        weight_elem = page.locator(
            f"xpath={_FALLBACK_WEIGHT_XPATH_TPL.format(idx=idx)}"
        )
        if name_elem.count() == 0 or weight_elem.count() == 0:
            continue
        name_text = name_elem.text_content().strip()
        if not name_text:
            continue
        holdings.append(
            Holding(
                name=name_text,
                weight=format_weight(weight_elem.text_content().strip()),
            )
        )
    return holdings


def _extract_holdings(page: Page) -> list[Holding]:
    """先試特徵定位，全空時退回絕對 XPath。"""
    primary = _extract_holdings_primary(page)
    if primary:
        return primary
    logger.info("Primary holdings extraction empty; using XPath fallback.")
    return _extract_holdings_fallback(page)


def _switch_to_value_tab(page: Page) -> bool:
    """以 dispatch_event 觸發頁籤切換，避免捲動卡死。"""
    try:
        tab_btn = page.wait_for_selector(_TAB_SELECTOR, state="visible", timeout=5000)
        if not tab_btn:
            return False
        tab_btn.scroll_into_view_if_needed()
        tab_btn.dispatch_event("click")
        page.wait_for_timeout(2000)
        return True
    except Exception as exc:
        logger.warning("Switch tab failed: %s", exc)
        return False


def fetch() -> StockPriceSnapshot | None:
    """執行 00403A 爬蟲流程。"""
    with headless_page() as page:
        logger.info("Loading %s", URL)
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning("Page load timeout.")
            return None

        update_time = extract_date_from_label(page)
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
    #     python -m backend.core.funds.crawlers.uni_00403a
    # JSON 結果輸出到 stdout、log 輸出到 stderr。
    from backend.core.funds._dev_runner import run_crawler_standalone

    run_crawler_standalone(fetch, CODE)
