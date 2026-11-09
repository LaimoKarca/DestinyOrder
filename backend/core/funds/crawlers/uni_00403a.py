# -*- coding: utf-8 -*-
"""00403A (主動統一升級50): validated official equity portfolio crawler.

The official investment portfolio includes summary tables and potentially
non-equity positions. Select the equity table by its column headings, not by
absolute XPath or a table's ordinal position.
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

CODE: Final[str] = "00403A"
NAME: Final[str] = "主動統一升級50"
URL: Final[str] = "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=63YTW"
_STOCK_HEADERS: Final[tuple[str, ...]] = ("股票代號", "股票名稱", "持股權重")
_WEIGHT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d+(?:\.\d+)?\s*%$")
_STOCK_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9A-Za-z]{4,8}$")
_MIN_STOCKS: Final[int] = 15


def _parse_stock_rows(rows: list[list[str]]) -> list[Holding] | None:
    """Parse a stock table, returning None for non-stock tables."""
    header_row = -1
    columns: dict[str, int] = {}
    for i, row in enumerate(rows[:4]):
        normalized = ["".join(cell.split()) for cell in row]
        if all(header in normalized for header in _STOCK_HEADERS):
            header_row = i
            columns = {header: normalized.index(header) for header in _STOCK_HEADERS}
            break
    if header_row < 0:
        return None

    stocks: list[Holding] = []
    seen: set[str] = set()
    for cells in rows[header_row + 1:]:
        if len(cells) <= max(columns.values()):
            continue
        code = cells[columns["股票代號"]].strip()
        name = cells[columns["股票名稱"]].strip()
        weight = cells[columns["持股權重"]].strip()
        if not code and not name:
            continue
        if not _STOCK_CODE_PATTERN.fullmatch(code) or not name:
            raise ValueError(f"00403A invalid stock identifier: {code!r}, {name!r}")
        if not _WEIGHT_PATTERN.fullmatch(weight):
            raise ValueError(f"00403A invalid weight for stock {code}: {weight!r}")
        if code in seen:
            raise ValueError(f"00403A duplicate stock identifier: {code}")
        seen.add(code)
        stocks.append(Holding(name=name, weight=format_weight(weight)))
    return stocks


def _validate_holdings(holdings: list[Holding]) -> float:
    """Reject truncated, non-equity, and impossible snapshots before writing."""
    if len(holdings) < _MIN_STOCKS:
        raise ValueError(f"00403A incomplete holdings: {len(holdings)} stocks")
    values = [float(item.weight.rstrip("%")) for item in holdings]
    if any(value < 0 or value > 100 for value in values):
        raise ValueError("00403A contains negative or impossible weights")
    total = sum(values)
    if not 20 <= total <= 102:
        raise ValueError(f"00403A implausible equity total: {total:.2f}%")
    return total


def _extract_holdings(page: Page) -> list[Holding]:
    """Find stock details by exact column headings in #assetBody."""
    tables = page.locator("#assetBody table")
    for i in range(tables.count()):
        rows = tables.nth(i).locator("tr").evaluate_all(
            "(trs) => trs.map(tr => Array.from(tr.querySelectorAll('th,td'),"
            " cell => (cell.textContent || '').trim()))"
        )
        holdings = _parse_stock_rows(rows)
        if holdings is not None:
            total = _validate_holdings(holdings)
            logger.info(
                "00403A official equity table validated: %s stocks, %.2f%% total",
                len(holdings), total,
            )
            return holdings
    raise ValueError("00403A official equity holdings table not found")


def _switch_to_value_tab(page: Page) -> bool:
    try:
        tab = page.locator("a[data-toggle='tab'][href='#value']").first
        if not tab.count():
            return False
        tab.evaluate("(element) => element.click()")
        page.wait_for_timeout(1200)
        return True
    except Exception as exc:
        logger.warning("00403A NAV tab switch failed: %s", exc)
        return False


def _fetch_once() -> StockPriceSnapshot:
    with headless_page() as page:
        response = page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        if response is not None and response.status >= 400:
            raise RuntimeError(f"00403A official source HTTP {response.status}")

        # Avoid networkidle: analytics or background requests need not settle.
        # Wait for the actual stock table, including a reasonable row count.
        page.wait_for_function(
            """() => Array.from(document.querySelectorAll('#assetBody table'))
                .some(t => {
                    const rows = t.querySelectorAll('tr');
                    const hasStockHeader = Array.from(rows).slice(0, 4)
                        .some(r => ['股票代號', '股票名稱', '持股權重']
                            .every(label => (r.textContent || '').includes(label)));
                    return rows.length >= 17 && hasStockHeader;
                })""",
            timeout=20000,
        )

        holdings = _extract_holdings(page)
        update_time = extract_date_from_label(page)
        nav, change = "未取得", "未取得"
        if _switch_to_value_tab(page):
            nav, change = extract_nav_from_value_tab(page)
    return StockPriceSnapshot(
        code=CODE, name=NAME, nav=nav, change_percent=change,
        update_time=update_time, holdings=holdings,
    )


def fetch() -> StockPriceSnapshot | None:
    """Retry one transient timeout; reject invalid data without publishing."""
    logger.info("Loading %s", URL)
    for attempt in (1, 2):
        try:
            return _fetch_once()
        except PlaywrightTimeoutError:
            logger.warning(
                "00403A official stock table timed out (attempt %s/2)", attempt
            )
    return None


if __name__ == "__main__":
    from backend.core.funds._dev_runner import run_crawler_standalone
    run_crawler_standalone(fetch, CODE)
