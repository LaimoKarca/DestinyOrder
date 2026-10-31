# -*- coding: utf-8-sig -*-
"""TWSE 有價證券清單爬蟲與排程器。

從台灣證券交易所（ISIN 查詢頁）抓取「上市 + 上櫃」證券清單，輸出至
``backend/data/funds/symbol.json`` 與 ``backend/data/funds/symbol.csv``。
排程依 :data:`TWSE_SECURITIES_RUN_TIMES`（預設每日 03:00 與 15:00）執行，
每次都會直接覆蓋舊檔。
"""

import csv
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

import requests
from lxml import html

from backend.core.funds._schedule_utils import format_times, seconds_until_next_run
from backend.core.shared.config import (
    ENCODING,
    FUNDS_DATA_ROOT,
    TWSE_SECURITIES_RUN_TIMES,
    TWSE_SECURITIES_SOURCES,
)
from backend.core.shared.json_storage import save_json
from backend.core.shared.log_handler import get_logger

logger = get_logger(__name__)

_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_REQUEST_TIMEOUT_SECS: Final[int] = 30
# TWSE ISIN 頁面為 Big5/MS950 編碼，需手動指定以防亂碼。
_PAGE_ENCODING: Final[str] = "big5"

_OUTPUT_CSV: Final[Path] = FUNDS_DATA_ROOT / "symbol.csv"
_OUTPUT_JSON: Final[Path] = FUNDS_DATA_ROOT / "symbol.json"
_CSV_FIELDS: Final[tuple[str, ...]] = (
    "symbol",
    "name",
    "listing_date",
    "industry",
    "market",
)

_UPDATE_DATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d{4}/\d{2}/\d{2})")
_SYMBOL_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^([A-Za-z0-9]+)\s+(.*)$")


def _fetch_page(url: str) -> str:
    """以 Big5 編碼下載 TWSE 頁面 HTML。"""
    logger.info("Fetching %s", url)
    response = requests.get(
        url,
        headers={"User-Agent": _USER_AGENT},
        timeout=_REQUEST_TIMEOUT_SECS,
    )
    response.raise_for_status()
    response.encoding = _PAGE_ENCODING
    return response.text


def _extract_update_date(tree: html.HtmlElement) -> str:
    """從 HTML 樹萃取「最近更新日期」字串，找不到則回傳空字串。"""
    for raw_text in tree.xpath("//text()[contains(., '最近更新日期')]"):
        match = _UPDATE_DATE_PATTERN.search(raw_text)
        if match:
            return match.group(1)
    logger.warning("Update date not found in page.")
    return ""


def _extract_securities(tree: html.HtmlElement, market: str) -> list[dict[str, str]]:
    """從第二個表格逐列萃取代號、名稱、上市日期、產業別，並附上 ``market`` 標籤。"""
    securities: list[dict[str, str]] = []
    # 避免使用瀏覽器自動補全的 <tbody>，改用 //tr 走全部列。
    rows = tree.xpath("/html/body/table[2]//tr")

    # 前兩列為標題與分類；資料自第三列起。
    for row in rows[2:]:
        cols = row.xpath("./td")
        if len(cols) < 5:
            continue

        raw_code_name = "".join(cols[0].itertext()).strip()
        if not raw_code_name:
            # 表格結尾常見為空白列，視為結束。
            break

        match = _SYMBOL_NAME_PATTERN.match(raw_code_name)
        if not match:
            continue

        securities.append(
            {
                "symbol": match.group(1),
                "name": match.group(2),
                "listing_date": "".join(cols[2].itertext()).strip(),
                "industry": "".join(cols[4].itertext()).strip(),
                "market": market,
            }
        )

    return securities


def _merge_securities(
    accumulated: list[dict[str, str]],
    incoming: list[dict[str, str]],
) -> list[dict[str, str]]:
    """把 ``incoming`` 併入 ``accumulated``，遇相同 ``symbol`` 時保留先到者。"""
    seen = {item["symbol"] for item in accumulated}
    for item in incoming:
        if item["symbol"] in seen:
            logger.warning(
                "Duplicate symbol %s across markets; keeping the earlier entry.",
                item["symbol"],
            )
            continue
        accumulated.append(item)
        seen.add(item["symbol"])
    return accumulated


def _write_csv(path: Path, securities: list[dict[str, str]]) -> None:
    """以 ``ENCODING`` 覆寫 CSV，欄位順序依 ``_CSV_FIELDS``。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=ENCODING, newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(_CSV_FIELDS))
        writer.writeheader()
        writer.writerows(securities)


def fetch_and_save() -> bool:
    """執行一次完整流程：抓所有來源 → 解析 → 合併 → 覆寫 CSV/JSON。

    依 ``TWSE_SECURITIES_SOURCES`` 逐一抓取上市 / 上櫃清單。單一來源失敗不會
    終止整體流程；只要至少一個來源回傳資料，就會覆寫 CSV/JSON。

    Returns:
        成功（合併後至少有一筆資料且檔案已寫入）回傳 ``True``，否則 ``False``。
        失敗時不會覆寫既有檔案，避免破壞先前有效資料。
    """
    started_at = datetime.now()
    logger.info(
        "TWSE securities batch start at %s (%d sources).",
        started_at.strftime("%Y-%m-%d %H:%M:%S"),
        len(TWSE_SECURITIES_SOURCES),
    )

    securities: list[dict[str, str]] = []
    update_date = ""

    for market, url in TWSE_SECURITIES_SOURCES:
        try:
            page_html = _fetch_page(url)
        except Exception:
            logger.exception("Failed to fetch %s (%s)", url, market)
            continue

        tree = html.fromstring(page_html)
        # 多來源時優先採用第一個有結果的更新日期（多半同步）。
        if not update_date:
            update_date = _extract_update_date(tree)

        parsed = _extract_securities(tree, market)
        logger.info("Parsed %d %s securities.", len(parsed), market)
        _merge_securities(securities, parsed)

    if not securities:
        logger.warning(
            "No securities parsed from any source; skipping file write to keep existing data."
        )
        return False

    logger.info(
        "Merged total %d securities (update_date=%s).",
        len(securities),
        update_date or "unknown",
    )

    _write_csv(_OUTPUT_CSV, securities)
    save_json({"update_date": update_date, "data": securities}, _OUTPUT_JSON)
    logger.info("Wrote %s and %s.", _OUTPUT_CSV, _OUTPUT_JSON)

    elapsed = (datetime.now() - started_at).total_seconds()
    logger.info("TWSE securities batch done, elapsed=%.1fs.", elapsed)
    return True


def run_forever() -> None:
    """常駐主迴圈：啟動立即執行，之後於每個排定時刻重新觸發。"""
    logger.info(
        "TWSE securities scheduler starting. Daily triggers at %s.",
        format_times(TWSE_SECURITIES_RUN_TIMES),
    )

    fetch_and_save()

    while True:
        wait_secs = seconds_until_next_run(TWSE_SECURITIES_RUN_TIMES)
        next_at = datetime.now() + timedelta(seconds=wait_secs)
        logger.info(
            "Sleeping until next TWSE securities run: %s (in %.0fs)",
            next_at.strftime("%Y-%m-%d %H:%M:%S"),
            wait_secs,
        )
        time.sleep(wait_secs)
        fetch_and_save()
