# -*- coding: utf-8-sig -*-
"""元大台灣卓越50基金（0050）爬蟲。

來源：https://www.yuantafunds.com/myfund/information/1066
分兩階段擷取：先讀淨值 / 漲跌幅 / 更新時間，再點擊持股切換鈕後讀十大持股。
"""

from typing import Final

from backend.core.shared.log_handler import get_logger
from backend.core.shared.playwright_helpers import (
    click_xpath,
    extract_texts_by_xpath,
    headless_page,
)
from backend.core.shared.text_cleaning import (
    normalize_change_percent,
    strip_parentheses,
)
from backend.schemas.stock_price import Holding, StockPriceSnapshot

logger = get_logger(__name__)

CODE: Final[str] = "0050"
NAME: Final[str] = "元大台灣卓越50基金"
URL: Final[str] = "https://www.yuantafunds.com/myfund/information/1066"

_NAV_XPATH: Final[str] = (
    "/html/body/div[1]/div/div/article/div[3]/section[1]/div[2]/div[2]/div/div[2]/div/p[1]"
)
_PERCENT_XPATH: Final[str] = (
    "/html/body/div[1]/div/div/article/div[3]/section[1]/div[2]/div[2]/div/div[3]/div/div/p[2]"
)
_TIME_XPATH: Final[str] = (
    "/html/body/div[1]/div/div/article/div[3]/section[1]/div[2]/div[2]/div/div[2]/div/p[2]"
)
_HOLDINGS_TAB_XPATH: Final[str] = (
    "/html/body/div[1]/div/div/article/div[3]/section[2]/div/div[2]"
)

_BASE_HOLDING_XPATH: Final[str] = (
    "/html/body/div[1]/div/div/article/div[3]/section[3]/div/section[4]/div/div[1]"
)
_HOLDING_NAME_CELLS: Final[tuple[tuple[int, int], ...]] = tuple(
    (col, row) for col in (1, 2) for row in range(2, 7)
)
_STOCK_NAME_XPATHS: Final[list[str]] = [
    f"{_BASE_HOLDING_XPATH}/div[{col}]/div[{row}]/div[2]/p"
    for col, row in _HOLDING_NAME_CELLS
]
_STOCK_WEIGHT_XPATHS: Final[list[str]] = [
    f"{_BASE_HOLDING_XPATH}/div[{col}]/div[{row}]/div[3]/p"
    for col, row in _HOLDING_NAME_CELLS
]


def fetch() -> StockPriceSnapshot | None:
    """執行 0050 爬蟲流程。

    Returns:
        擷取成功回傳 :class:`StockPriceSnapshot`，失敗回傳 None。
    """
    pre_xpaths = [_NAV_XPATH, _PERCENT_XPATH, _TIME_XPATH]
    post_xpaths = _STOCK_NAME_XPATHS + _STOCK_WEIGHT_XPATHS

    with headless_page() as page:
        logger.info("Loading %s", URL)
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
        except Exception:
            logger.exception("Failed to load page: %s", URL)
            return None

        pre_data = extract_texts_by_xpath(page, pre_xpaths)

        if not click_xpath(page, _HOLDINGS_TAB_XPATH):
            logger.warning("Holdings tab click failed; data may be incomplete.")

        post_data = extract_texts_by_xpath(page, post_xpaths)

    holdings = [
        Holding(
            name=post_data.get(name_xp, "未取得"),
            weight=post_data.get(weight_xp, "未取得"),
        )
        for name_xp, weight_xp in zip(_STOCK_NAME_XPATHS, _STOCK_WEIGHT_XPATHS)
    ]

    return StockPriceSnapshot(
        code=CODE,
        name=NAME,
        nav=pre_data.get(_NAV_XPATH, "未取得"),
        change_percent=normalize_change_percent(pre_data.get(_PERCENT_XPATH, "未取得")),
        update_time=strip_parentheses(pre_data.get(_TIME_XPATH, "未取得")),
        holdings=holdings,
    )


if __name__ == "__main__":
    # 單獨執行此爬蟲（偵錯 / 單元測試 / 維護用）。
    # 於專案根目錄 (DestinyOrder/) 執行：
    #     python -m backend.core.funds.crawlers.yuanta_0050
    # JSON 結果輸出到 stdout、log 輸出到 stderr。
    # 也可重導向只取結果：
    #     python -m backend.core.funds.crawlers.yuanta_0050 > out.json
    from backend.core.funds._dev_runner import run_crawler_standalone

    run_crawler_standalone(fetch, CODE)
