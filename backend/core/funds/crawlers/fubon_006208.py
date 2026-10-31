# -*- coding: utf-8-sig -*-
"""富邦台50（006208）爬蟲。

來源：富邦投信 ETF 網頁，概況頁取得淨值與漲跌幅，資產頁讀取前 50
大持股明細。網頁開啟時可能跳出風險同意彈窗，需先關閉。
"""

from datetime import datetime
from typing import Final

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from backend.core.shared.log_handler import get_logger
from backend.core.shared.playwright_helpers import (
    extract_text_by_xpath,
    headless_page,
)
from backend.core.shared.text_cleaning import (
    format_weight,
    normalize_change_percent,
)
from backend.schemas.stock_price import Holding, StockPriceSnapshot

logger = get_logger(__name__)

CODE: Final[str] = "006208"
NAME: Final[str] = "富邦台50"
URL_PROFILE: Final[str] = "https://websys.fsit.com.tw/FubonETF/Fund/Profile.aspx?stkId=006208"
URL_ASSETS: Final[str] = "https://websys.fsit.com.tw/FubonETF/Fund/Assets.aspx?stkId=006208"

_POPUP_XPATH: Final[str] = "/html/body/div[2]/div/div[2]/div[2]/div/button"
_NAV_XPATH: Final[str] = (
    "/html/body/form/article/div/div/div/div[2]/div[2]/div[2]/div[1]/p[2]"
)
_PERCENT_XPATH: Final[str] = (
    "/html/body/form/article/div/div/div/div[2]/div[2]/div[1]/div[2]/div[3]/p[2]"
)
_HOLDINGS_TABLE_XPATH: Final[str] = (
    "/html/body/form/article/div/div/div/div[2]/div[3]/div[2]/table/tbody"
)
_HOLDINGS_START_ROW: Final[int] = 2
_HOLDINGS_END_ROW: Final[int] = 51


def _close_popup_if_present(page: Page, timeout: int = 3000) -> None:
    """若風險同意彈窗存在則關閉，否則靜默略過。"""
    try:
        element = page.wait_for_selector(
            f"xpath={_POPUP_XPATH}",
            state="visible",
            timeout=timeout,
        )
        if element:
            element.scroll_into_view_if_needed()
            element.click(force=True)
            page.wait_for_timeout(1000)
    except PlaywrightTimeoutError:
        pass
    except Exception as exc:
        logger.warning("Popup close failed: %s", exc)


def _extract_holdings(page: Page) -> list[Holding]:
    """從資產頁的持股表格擷取所有持股明細。"""
    first_row_xpath = (
        f"{_HOLDINGS_TABLE_XPATH}/tr[{_HOLDINGS_START_ROW}]/td[2]"
    )
    try:
        page.wait_for_selector(f"xpath={first_row_xpath}", timeout=8000)
    except PlaywrightTimeoutError:
        logger.warning("Holdings table not ready; structure may have changed.")
        return []

    holdings: list[Holding] = []
    for row_idx in range(_HOLDINGS_START_ROW, _HOLDINGS_END_ROW + 1):
        name_xpath = f"{_HOLDINGS_TABLE_XPATH}/tr[{row_idx}]/td[2]"
        weight_xpath = f"{_HOLDINGS_TABLE_XPATH}/tr[{row_idx}]/td[5]"

        name_locator = page.locator(f"xpath={name_xpath}")
        weight_locator = page.locator(f"xpath={weight_xpath}")

        stock_name = (
            name_locator.text_content().strip()
            if name_locator.count() > 0
            else "未取得"
        )
        raw_weight = (
            weight_locator.text_content().strip()
            if weight_locator.count() > 0
            else "未取得"
        )

        if stock_name == "未取得":
            continue

        holdings.append(Holding(name=stock_name, weight=format_weight(raw_weight)))

    return holdings


def fetch() -> StockPriceSnapshot | None:
    """執行 006208 爬蟲流程。

    Returns:
        擷取成功回傳 :class:`StockPriceSnapshot`，失敗回傳 None。
    """
    with headless_page() as page:
        logger.info("Loading profile page: %s", URL_PROFILE)
        try:
            page.goto(URL_PROFILE, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning("Profile page load timeout.")
            return None

        _close_popup_if_present(page)
        raw_nav = extract_text_by_xpath(page, _NAV_XPATH)
        raw_percent = extract_text_by_xpath(page, _PERCENT_XPATH)

        logger.info("Loading assets page: %s", URL_ASSETS)
        try:
            page.goto(URL_ASSETS, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning("Assets page load timeout.")
            return None

        _close_popup_if_present(page, timeout=2000)
        holdings = _extract_holdings(page)

    return StockPriceSnapshot(
        code=CODE,
        name=NAME,
        nav=raw_nav,
        change_percent=normalize_change_percent(raw_percent),
        update_time=datetime.now().strftime("%Y/%m/%d"),
        holdings=holdings,
    )


if __name__ == "__main__":
    # 單獨執行此爬蟲（偵錯 / 單元測試 / 維護用）。
    # 於專案根目錄 (DestinyOrder/) 執行：
    #     python -m backend.core.funds.crawlers.fubon_006208
    # JSON 結果輸出到 stdout、log 輸出到 stderr。
    from backend.core.funds._dev_runner import run_crawler_standalone

    run_crawler_standalone(fetch, CODE)
