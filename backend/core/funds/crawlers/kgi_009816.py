# -*- coding: utf-8-sig -*-
"""凱基台灣 TOP50 基金（009816）爬蟲。

來源：凱基投信基金詳細頁。透過精確 CSS 選擇器擷取淨值與漲跌幅，並依
HTML class / img 特徵判斷漲跌正負號；持股表透過點擊「看更多」展開。
"""

from typing import Final

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from backend.core.shared.log_handler import get_logger
from backend.core.shared.playwright_helpers import headless_page
from backend.core.shared.text_cleaning import (
    extract_date_or_today,
    extract_numeric,
    format_weight,
    is_invalid_token,
)
from backend.schemas.stock_price import Holding, StockPriceSnapshot

logger = get_logger(__name__)

CODE: Final[str] = "009816"
NAME: Final[str] = "凱基台灣TOP50基金"
URL: Final[str] = "https://www.kgifund.com.tw/Fund/Detail?fundID=J023"

_NAV_CSS: Final[str] = (
    "body > div.DetailNavDiv.paddingB-075r.marginB-175r.md-position-St.fixed > "
    "div > div > div.col-12.col-lg-5.display-F.xl-justifyC-C.lg-paddingL-15 > "
    "div.DetailNavDiv-info.marginR-075r.md-margin-0 > "
    "p.textC-blue.fontS-200r.fontW-600.borderR-G.marginB-025r.paddingR-075r"
)
_CHANGE_CSS: Final[str] = (
    "body > div.DetailNavDiv.paddingB-075r.marginB-175r.md-position-St.fixed > "
    "div > div > div.col-12.col-lg-5.display-F.xl-justifyC-C.lg-paddingL-15 > "
    "div.DetailNavDiv-info2.marginR-075r.md-margin-0 > "
    "p.detail-padding-RWD.d-flex.align-items-center.md-marginL-5.textC-red."
    "fontS-200r.fontW-600.borderR-G.marginB-025r"
)
_RISE_CLASS_TOKEN: Final[str] = "textC-red"
_RISE_IMG_TOKEN: Final[str] = "Rise.svg"

_HOLDINGS_TABLE_FEATURES: Final[tuple[str, ...]] = (
    "table:has-text('名稱'):has-text('權重')",
    "table:has-text('台積電')",
)
_EXPAND_BUTTON_SELECTOR: Final[str] = (
    "a:has-text('看更多'), span:has-text('看更多')"
)
_MAX_EXPAND_CLICKS: Final[int] = 4
_HOLDINGS_END_IDX: Final[int] = 50


def _dismiss_risk_popup(page: Page) -> None:
    """以 JavaScript 同意風險聲明 / 隱藏 Modal。"""
    try:
        page.evaluate(
            """
            try {
                if (typeof ClickETFWarningOption === 'function') {
                    ClickETFWarningOption('同意');
                }
                const modals = document.querySelectorAll('.modal, .modal-backdrop');
                modals.forEach(m => m.style.display = 'none');
            } catch (e) { }
            """
        )
        page.wait_for_timeout(2000)
    except Exception as exc:
        logger.warning("Dismiss risk popup failed: %s", exc)


def _extract_nav_and_change(page: Page) -> tuple[str, str]:
    """擷取淨值與漲跌幅；透過 HTML 特徵判定正負號。"""
    nav_text = "未取得"
    change_text = "未取得"

    try:
        page.wait_for_selector(_NAV_CSS, timeout=5000)
        nav_locator = page.locator(_NAV_CSS)
        if nav_locator.count() > 0:
            nav_text = extract_numeric(nav_locator.text_content().strip())
    except Exception as exc:
        logger.warning("Extract NAV failed: %s", exc)

    try:
        page.wait_for_selector(_CHANGE_CSS, timeout=5000)
        change_locator = page.locator(_CHANGE_CSS)
        if change_locator.count() > 0:
            raw_change = change_locator.text_content().strip()
            clean_num = extract_numeric(raw_change)

            class_attr = change_locator.get_attribute("class") or ""
            img_locator = change_locator.locator("img")
            img_src = (
                img_locator.first.get_attribute("src") or ""
                if img_locator.count() > 0
                else ""
            )

            is_rising = (
                _RISE_CLASS_TOKEN in class_attr or _RISE_IMG_TOKEN in img_src
            )
            sign = "+" if is_rising else "-"
            change_text = f"{sign}{clean_num}%"
    except Exception as exc:
        logger.warning("Extract change percent failed: %s", exc)

    return nav_text, change_text


def _expand_holdings_table(page: Page) -> None:
    """循環點擊「看更多」按鈕展開完整持股表。"""
    for attempt in range(1, _MAX_EXPAND_CLICKS + 1):
        try:
            btn = page.locator(_EXPAND_BUTTON_SELECTOR).locator("visible=true").first
            if btn.count() == 0 or not btn.is_visible(timeout=5000):
                break
            btn.scroll_into_view_if_needed()
            btn.dispatch_event("click")
            page.wait_for_timeout(2000)
        except Exception as exc:
            logger.warning("Expand attempt %d failed: %s", attempt, exc)
            break


def _locate_holdings_table(page: Page):
    """依序以特徵選擇器找尋持股表，回傳第一個命中的 locator。"""
    for selector in _HOLDINGS_TABLE_FEATURES:
        target = page.locator(selector).first
        if target.count() > 0:
            return target
    return None


def _extract_holdings(page: Page) -> list[Holding]:
    """擷取展開後的持股名稱與權重。"""
    target_table = _locate_holdings_table(page)
    if target_table is None:
        logger.warning("Cannot locate holdings table by feature.")
        return []

    try:
        target_table.locator("tbody tr").first.wait_for(
            state="attached", timeout=5000
        )
    except PlaywrightTimeoutError:
        logger.warning("Holdings table rows not attached.")
        return []

    rows = target_table.locator("tbody tr")
    total_rows = rows.count()
    holdings: list[Holding] = []

    for i in range(1, min(_HOLDINGS_END_IDX + 1, total_rows + 1)):
        row = rows.nth(i - 1)
        name_cell = row.locator("td").nth(1)
        weight_cell = row.locator("td").nth(3)

        if name_cell.count() == 0 or weight_cell.count() == 0:
            continue

        stock_name = name_cell.text_content().strip()
        if is_invalid_token(stock_name):
            continue

        holdings.append(
            Holding(
                name=stock_name,
                weight=format_weight(weight_cell.text_content().strip()),
            )
        )
    return holdings


def fetch() -> StockPriceSnapshot | None:
    """執行 009816 爬蟲流程。"""
    with headless_page() as page:
        logger.info("Loading %s", URL)
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning("Page load timeout.")
            return None

        _dismiss_risk_popup(page)
        nav_text, change_text = _extract_nav_and_change(page)
        body_text = page.locator("body").text_content() or ""
        update_time = extract_date_or_today(body_text)

        page.evaluate("window.scrollBy(0, 800)")
        page.wait_for_timeout(1000)

        _expand_holdings_table(page)
        holdings = _extract_holdings(page)

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
    #     python -m backend.core.funds.crawlers.kgi_009816
    # JSON 結果輸出到 stdout、log 輸出到 stderr。
    from backend.core.funds._dev_runner import run_crawler_standalone

    run_crawler_standalone(fetch, CODE)
