# -*- coding: utf-8-sig -*-
"""權重查詢資料聚合邏輯。

職責：依「ETF 分組」回傳各檔 ETF 的成分股明細，並補上 TWSE 證券代號。
與 :mod:`lucky_aggregator`（依「股票」分組做抽抽樂）為兩種不同視角，
但共用底層工具（找最新日期資料夾、讀 snapshot、讀 symbol.json）。
"""

from pathlib import Path

from backend.core.funds.lucky_aggregator import (
    _load_snapshots,
    _load_symbol_lookup,
    _normalize_stock_name,
    _relative_date_label,
    find_latest_dated_dir,
)
from backend.core.funds.registry import CRAWLERS
from backend.core.shared.config import FUNDS_DATA_ROOT
from backend.core.shared.log_handler import get_logger
from backend.schemas.funds_etf import EtfDetail, EtfHolding, FundsByEtfResponse

logger = get_logger(__name__)


def build_by_etf_response(
    base: Path = FUNDS_DATA_ROOT,
) -> FundsByEtfResponse | None:
    """組裝權重查詢 API 回應；找不到資料時回傳 ``None``。

    輸出順序依照 ``CRAWLERS`` 註冊順序，方便前端下拉選單呈現一致排列。
    """
    latest_dir = find_latest_dated_dir(base)
    if latest_dir is None:
        logger.warning("No dated funds folder found under %s", base)
        return None

    snapshots = _load_snapshots(latest_dir)
    if not snapshots:
        logger.warning(
            "Latest dir %s exists but contains no readable snapshots", latest_dir
        )
        return None

    symbol_lookup = _load_symbol_lookup(base)

    etfs: list[EtfDetail] = []
    for entry in CRAWLERS:
        snapshot = snapshots.get(entry.code)
        if snapshot is None:
            # 缺一檔不影響其他檔，跳過後繼續組
            continue
        holdings: list[EtfHolding] = []
        for h in snapshot.holdings:
            normalized = _normalize_stock_name(h.name)
            lookup_hit = symbol_lookup.get(normalized) if normalized else None
            holdings.append(
                EtfHolding(
                    name=normalized or h.name,
                    symbol=lookup_hit["symbol"] if lookup_hit else None,
                    weight=h.weight,
                )
            )
        etfs.append(
            EtfDetail(
                code=entry.code,
                name=snapshot.name,
                update_time=snapshot.update_time,
                source_url=entry.source_url,
                holdings=holdings,
            )
        )

    if not etfs:
        return None

    return FundsByEtfResponse(
        date=_relative_date_label(latest_dir, base),
        etfs=etfs,
    )
