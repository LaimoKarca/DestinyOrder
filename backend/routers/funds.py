# -*- coding: utf-8-sig -*-
"""基金抽抽樂相關路由。

不在路由層直接讀檔，所有檔案存取與聚合邏輯都委派給
``backend.core.funds.lucky_aggregator``。
"""

from fastapi import APIRouter, HTTPException, status

from backend.core.funds.etf_aggregator import build_by_etf_response
from backend.core.funds.lucky_aggregator import build_lucky_response
from backend.core.shared.log_handler import get_logger
from backend.schemas.funds_etf import FundsByEtfResponse
from backend.schemas.funds_lucky import FundsLuckyResponse

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/funds",
    tags=["funds"],
)


@router.get("/latest")
def get_latest_lucky_pool() -> FundsLuckyResponse:
    """取得最新日期資料夾彙整出的抽抽樂股票池。"""
    response = build_lucky_response()
    if response is None:
        logger.warning("get_latest_lucky_pool: no data available")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未抓取到任何基金資料；請先執行爬蟲。",
        )
    return response


@router.get("/by_etf")
def get_by_etf_breakdown() -> FundsByEtfResponse:
    """取得最新日期下，依 ETF 分組的成分股明細（含官方來源網址）。"""
    response = build_by_etf_response()
    if response is None:
        logger.warning("get_by_etf_breakdown: no data available")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未抓取到任何基金資料；請先執行爬蟲。",
        )
    return response
