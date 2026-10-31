# -*- coding: utf-8-sig -*-
"""抽抽樂股票池聚合邏輯。

職責：
1. 在 ``FUNDS_DATA_ROOT`` 之下搜尋「最新日期資料夾」（``yyyy/mm/dd`` 結構）。
2. 讀取該資料夾內已註冊 ETF 的 JSON 快照。
3. 比對 ``symbol.json``（TWSE 證券清單）補上代號與產業別。
4. 輸出 ``FundsLuckyResponse``，供路由直接回傳。

聚合策略：以「股票名稱」做為 key，同一支股票在多檔 ETF 同時出現時，
將每個來源（ETF + 權重）紀錄在 ``sources`` 中。
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Final

from backend.core.funds.registry import CRAWLERS
from backend.core.shared.config import ENCODING, FUNDS_DATA_ROOT
from backend.core.shared.log_handler import get_logger
from backend.schemas.funds_lucky import (
    DrawableStock,
    DrawSource,
    FundsLuckyResponse,
)
from backend.schemas.stock_price import StockPriceSnapshot

logger = get_logger(__name__)

SYMBOL_FILE: Final[Path] = FUNDS_DATA_ROOT / "symbol.json"
_YEAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{4}$")
_MONTH_DAY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{2}$")

# 跨投信持股名稱與 TWSE symbol.json 簡稱之精確別名映射（不做模糊截字）
_STOCK_NAME_ALIASES: Final[dict[str, str]] = {
    "創意電子": "創意",
}


def _list_sorted_desc(parent: Path, pattern: re.Pattern[str]) -> list[str]:
    """列出 ``parent`` 下符合 ``pattern`` 的子目錄名稱，由新到舊排序。"""
    if not parent.is_dir():
        return []
    return sorted(
        (item.name for item in parent.iterdir() if item.is_dir() and pattern.match(item.name)),
        reverse=True,
    )


def find_latest_dated_dir(
    base: Path = FUNDS_DATA_ROOT,
    required_codes: tuple[str, ...] = tuple(entry.code for entry in CRAWLERS),
) -> Path | None:
    """搜尋 ``base`` 之下最新含有任一 ETF 快照的 ``yyyy/mm/dd`` 子目錄。

    搜尋策略：年→月→日皆採字典序倒排，命中第一個含至少一支 ``required_codes``
    JSON 檔案的資料夾即回傳；找不到時回傳 ``None``。

    Args:
        base: 基金資料夾根目錄。
        required_codes: 至少要有其中一個 ``<code>.json`` 才視為有效資料夾。

    Returns:
        最新日期資料夾的絕對路徑，或 ``None``。
    """
    for year in _list_sorted_desc(base, _YEAR_PATTERN):
        year_dir = base / year
        for month in _list_sorted_desc(year_dir, _MONTH_DAY_PATTERN):
            month_dir = year_dir / month
            for day in _list_sorted_desc(month_dir, _MONTH_DAY_PATTERN):
                day_dir = month_dir / day
                if any((day_dir / f"{code}.json").is_file() for code in required_codes):
                    return day_dir
    return None


def _normalize_stock_name(raw: str) -> str:
    """去除股票名稱尾端的 ``*`` 等狀態標記與空白，並套用精確別名映射。

    例：``"國巨*"`` → ``"國巨"``、``" 台積電 "`` → ``"台積電"``、``"創意電子"`` → ``"創意"``。
    """
    cleaned = raw.strip().rstrip("*").strip()
    return _STOCK_NAME_ALIASES.get(cleaned, cleaned)


def _read_json(path: Path) -> dict:
    """讀取以 ``ENCODING`` 編碼的 JSON 檔。"""
    return json.loads(path.read_text(encoding=ENCODING))


def _load_snapshots(latest_dir: Path) -> dict[str, StockPriceSnapshot]:
    """讀取最新日期資料夾下所有已註冊 ETF 的 snapshot。"""
    snapshots: dict[str, StockPriceSnapshot] = {}
    for entry in CRAWLERS:
        file_path = latest_dir / f"{entry.code}.json"
        if not file_path.is_file():
            logger.warning(
                "Snapshot missing for ETF %s in %s; skipped", entry.code, latest_dir
            )
            continue
        try:
            snapshots[entry.code] = StockPriceSnapshot.model_validate(
                _read_json(file_path)
            )
        except Exception:
            logger.exception(
                "Failed to parse snapshot %s; skipped", file_path
            )
    return snapshots


def _load_symbol_lookup(base: Path = FUNDS_DATA_ROOT) -> dict[str, dict[str, str]]:
    """讀取 ``base / symbol.json`` 並建立「名稱 → {symbol, industry}」對應表。

    僅讀取傳入之 ``base`` 目錄下的 ``symbol.json``，絕不回退讀取其他資料根目錄，
    確保隔離測試或示範目錄不會意外混入本機真實 ``symbol.json``。
    """
    symbol_path = base / "symbol.json"
    if not symbol_path.is_file():
        logger.warning("symbol.json not found at %s; lookup will be empty", symbol_path)
        return {}
    raw = _read_json(symbol_path)
    lookup: dict[str, dict[str, str]] = {}
    for entry in raw.get("data", []):
        name = _normalize_stock_name(entry.get("name", ""))
        if not name:
            continue
        lookup[name] = {
            "symbol": entry.get("symbol", ""),
            "industry": entry.get("industry", ""),
        }
    return lookup


def _relative_date_label(latest_dir: Path, base: Path = FUNDS_DATA_ROOT) -> str:
    """依傳入之 ``base`` 將日期資料夾轉成 ``yyyy/mm/dd`` 字串。"""
    try:
        return latest_dir.relative_to(base).as_posix()
    except ValueError:
        return latest_dir.name


def build_lucky_response(
    base: Path = FUNDS_DATA_ROOT,
    today: date | None = None,
) -> FundsLuckyResponse | None:
    """組裝抽抽樂 API 回應；找不到資料時回傳 ``None``。

    Args:
        base: 基金資料根目錄。
        today: 保留參數（目前未使用，預期用於未來「指定日期」功能）。

    Returns:
        聚合後的 :class:`FundsLuckyResponse`，或 ``None`` 表示無可用資料。
    """
    del today  # currently unused; placeholder for future date-pinning feature

    latest_dir = find_latest_dated_dir(base)
    if latest_dir is None:
        logger.warning("No dated funds folder found under %s", base)
        return None

    snapshots = _load_snapshots(latest_dir)
    if not snapshots:
        logger.warning("Latest dir %s exists but contains no readable snapshots", latest_dir)
        return None

    symbol_lookup = _load_symbol_lookup(base)
    bucket: dict[str, DrawableStock] = {}

    for etf_code, snapshot in snapshots.items():
        for holding in snapshot.holdings:
            normalized = _normalize_stock_name(holding.name)
            if not normalized:
                continue

            source = DrawSource(
                etf_code=etf_code,
                etf_name=snapshot.name,
                weight=holding.weight,
            )

            existing = bucket.get(normalized)
            if existing is not None:
                existing.sources.append(source)
                continue

            lookup_hit = symbol_lookup.get(normalized)
            bucket[normalized] = DrawableStock(
                name=normalized,
                symbol=lookup_hit["symbol"] if lookup_hit else None,
                industry=lookup_hit["industry"] if lookup_hit else None,
                sources=[source],
            )

    stocks = sorted(bucket.values(), key=lambda item: item.name)

    return FundsLuckyResponse(
        date=_relative_date_label(latest_dir, base),
        etf_codes=list(snapshots.keys()),
        stocks=stocks,
    )
