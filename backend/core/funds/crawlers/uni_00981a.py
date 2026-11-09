# -*- coding: utf-8 -*-
"""00981A (主動統一台股增長) official portfolio crawler.

The portfolio has distinct futures and equity tables. Only the equity
table headed 股票代號 / 股票名稱 / 持股權重 may become stock holdings.
Never publish a partial or implausible portfolio as a successful crawl.
"""
import re
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
URL: Final[str] = "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=49YTW"
_HEADERS: Final[tuple[str, ...]] = ("股票代號", "股票名稱", "持股權重")
_MIN_HOLDINGS: Final[int] = 15
_WEIGHT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d+(?:\.\d+)?\s*%$")
_STOCK_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9A-Za-z]{4,8}$")


def _clean_header(text: str) -> str:
    return "".join(text.split())


def _parse_stock_rows(rows: list[list[str]]) -> list[Holding] | None:
    """Return only stock holdings; None means this is not the equity table."""
    header_index = -1
    indices: dict[str, int] = {}
    for i, row in enumerate(rows[:4]):
        normalized = [_clean_header(cell) for cell in row]
        if all(header in normalized for header in _HEADERS):
            header_index = i
            indices = {header: normalized.index(header) for header in _HEADERS}
            break
    if header_index == -1:
        return None

    holdings: list[Holding] = []
    codes: set[str] = set()
    for row in rows[header_index + 1:]:
        if len(row) <= max(indices.values()):
            continue
        code = row[indices["股票代號"]].strip()
        name = row[indices["股票名稱"]].strip()
        weight_text = row[indices["持股權重"]].strip()
        if not code or not name:
            continue
        if not _STOCK_CODE_PATTERN.fullmatch(code):
            raise ValueError(f"Invalid stock code in 00981A portfolio: {code!r}")
        if not _WEIGHT_PATTERN.fullmatch(weight_text):
            raise ValueError(f"Invalid stock weight for {code}: {weight_text!r}")
        if code in codes:
            raise ValueError(f"Duplicate stock code in 00981A portfolio: {code}")
        codes.add(code)
        holdings.append(Holding(name=name, weight=format_weight(weight_text)))
    return holdings


def _validate_portfolio(holdings: list[Holding]) -> None:
    """Reject futures-only, truncated, or obviously incorrect stock snapshots."""
    if len(holdings) < _MIN_HOLDINGS:
        raise ValueError(
            f"00981A incomplete equity portfolio: {len(holdings)} rows "
            f"(minimum {_MIN_HOLDINGS}); refusing to overwrite saved data"
        )
    weights = [float(item.weight.rstrip("%")) for item in holdings]
    weight_sum = sum(weights)
    # The official source can round tiny residual positions to 0.00%.
    if any(weight < 0 or weight > 100 for weight in weights):
        raise ValueError("00981A has negative or impossible individual weights")
    if not 20 <= weight_sum <= 102:
        raise ValueError(
            f"00981A implausible equity weight total: {weight_sum:.2f}%; "
            "refusing to overwrite saved data"
        )


def _extract_holdings(page: Page) -> list[Holding]:
    """Locate the equity table by semantic column headers, not table position."""
    tables = page.locator("#assetBody table")
    for index in range(tables.count()):
        rows = tables.nth(index).locator("tr").evaluate_all(
            "(trs) => trs.map(tr => Array.from(tr.querySelectorAll('th,td'),"
            " cell => (cell.textContent || '').trim()))"
        )
        holdings = _parse_stock_rows(rows)
        if holdings is not None:
            _validate_portfolio(holdings)
            logger.info(
                "00981A official equity table validated: %s stocks, %.2f%% total",
                len(holdings),
                sum(float(item.weight.rstrip("%")) for item in holdings),
            )
            return holdings
    raise ValueError("00981A official equity holdings table not found in #assetBody")


def _switch_to_value_tab(page: Page) -> bool:
    """Switch to the NAV tab without relying on absolute XPath."""
    try:
        tab = page.locator("a[data-toggle='tab'][href='#value']").first
        if not tab.count():
            return False
        tab.evaluate("(el) => el.click()")
        page.wait_for_timeout(1500)
        return True
    except Exception as exc:
        logger.warning("Switch to 00981A NAV tab failed: %s", exc)
        return False


def fetch() -> StockPriceSnapshot | None:
    with headless_page() as page:
        logger.info("Loading %s", URL)
        try:
            response = page.goto(URL, wait_until="domcontentloaded", timeout=30000)
            # The page can keep unrelated network requests open indefinitely.
            # Wait for the actual equity table instead of global networkidle.
            page.wait_for_function(
                """() => Array.from(document.querySelectorAll('#assetBody table'))
                    .some(t => t.textContent.includes('股票代號')
                            && t.textContent.includes('股票名稱')
                            && t.textContent.includes('持股權重'))""",
                timeout=20000,
            )
        except PlaywrightTimeoutError:
            logger.warning("00981A official stock table did not load in time")
            return None
        if response is not None and response.status >= 400:
            raise RuntimeError(f"00981A official source HTTP {response.status}")

        # Portfolio content is available in the DOM even when the tab is hidden.
        update_time = extract_date_from_label(page)
        holdings = _extract_holdings(page)

        nav_text, change_text = "未取得", "未取得"
        if _switch_to_value_tab(page):
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
    from backend.core.funds._dev_runner import run_crawler_standalone
    run_crawler_standalone(fetch, CODE)
