# -*- coding: utf-8-sig -*-
"""依序執行所有基金爬蟲並儲存結果。

輸出檔案位於 ``backend/data/funds/<yyyy>/<mm>/<dd>/<code>.json``，
每次執行均無條件覆寫（檔案不存在會建立）。任一 crawler 例外不會影響
其餘 crawler 的執行。
"""

from datetime import datetime
from pathlib import Path

from backend.core.funds.registry import CRAWLERS, CrawlerEntry
from backend.core.shared.config import FUNDS_DATA_ROOT
from backend.core.shared.json_storage import build_dated_dir, save_json
from backend.core.shared.log_handler import get_logger
from backend.schemas.stock_price import StockPriceSnapshot

logger = get_logger(__name__)


def _persist_snapshot(snapshot: StockPriceSnapshot, target_dir: Path) -> Path:
    """以 ``<code>.json`` 為檔名寫出 Pydantic 序列化結果。"""
    output_path = target_dir / f"{snapshot.code}.json"
    save_json(snapshot.model_dump(), output_path)
    return output_path


def _run_single(entry: CrawlerEntry, target_dir: Path) -> bool:
    """執行單一爬蟲並寫檔，回傳是否成功。"""
    logger.info("Crawler start: %s (%s)", entry.code, entry.name)
    try:
        snapshot = entry.fetch()
    except Exception:
        logger.exception("Crawler %s raised unexpected exception", entry.code)
        return False

    if snapshot is None:
        logger.warning("Crawler %s returned no data", entry.code)
        return False

    output_path = _persist_snapshot(snapshot, target_dir)
    logger.info("Crawler done: %s -> %s", entry.code, output_path)
    return True


def run_all() -> None:
    """依序執行所有爬蟲並覆寫當日輸出資料夾。"""
    started_at = datetime.now()
    target_dir = build_dated_dir(FUNDS_DATA_ROOT, started_at)
    logger.info(
        "Batch start at %s, output_dir=%s, n_crawlers=%d",
        started_at.strftime("%Y-%m-%d %H:%M:%S"),
        target_dir,
        len(CRAWLERS),
    )

    success_count = sum(1 for entry in CRAWLERS if _run_single(entry, target_dir))

    elapsed = (datetime.now() - started_at).total_seconds()
    logger.info(
        "Batch done: %d/%d succeeded, elapsed=%.1fs",
        success_count,
        len(CRAWLERS),
        elapsed,
    )
