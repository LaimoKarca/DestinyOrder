# -*- coding: utf-8-sig -*-
"""集中 logger 取得介面。

所有模組透過 :func:`get_logger` 取得 logger，避免各處重複設定 handler
或散用 ``print()``。第一次呼叫時會替 root logger 安裝預設 StreamHandler。
"""

import logging
import sys
from typing import Final

_DEFAULT_FORMAT: Final[str] = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DEFAULT_DATEFMT: Final[str] = "%Y-%m-%d %H:%M:%S"


def _ensure_root_configured() -> None:
    """為 root logger 安裝預設 stdout handler（僅執行一次）。"""
    root = logging.getLogger()
    if root.handlers:
        return
    # 故意送 stderr：CLI 單跑單一爬蟲時，stdout 留給 JSON 結果，stderr 收 log，
    # 兩者不互相干擾（亦符合 12-Factor 慣例）。
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """取得已設定好輸出格式的 logger。

    Args:
        name: 通常傳入 ``__name__``。

    Returns:
        對應名稱的 logger 實例。
    """
    _ensure_root_configured()
    return logging.getLogger(name)
