# -*- coding: utf-8-sig -*-
"""集中設定模組。

匯出全專案會用到的路徑常數、檔案編碼與排程時刻。所有業務模組
**禁止** 自行硬編碼路徑字串，一律從此模組取得。
"""

import os
from pathlib import Path
from typing import Final

# 統一檔案編碼。所有 read_text / write_text / open 一律帶此參數。
ENCODING: Final[str] = "utf-8-sig"

# 路徑常數（支援透過環境變數覆寫資料目錄，便於本機示範資料或容器掛載）
BACKEND_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
PROJECT_ROOT: Final[Path] = BACKEND_ROOT.parent
_DEFAULT_DATA_ROOT: Final[Path] = BACKEND_ROOT / "data"


def resolve_configured_path(
    env_var: str,
    default_path: Path,
    base_root: Path = PROJECT_ROOT,
) -> Path:
    """解析資料路徑環境變數：空字串/純空白回退至 default_path，相對路徑固定相對於 PROJECT_ROOT。"""
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return default_path.resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = base_root / candidate
    return candidate.resolve()


DATA_ROOT: Final[Path] = resolve_configured_path(
    "DESTINYORDER_DATA_ROOT",
    _DEFAULT_DATA_ROOT,
)
FUNDS_DATA_ROOT: Final[Path] = resolve_configured_path(
    "DESTINYORDER_FUNDS_DATA_ROOT",
    DATA_ROOT / "funds",
)

# 排程時刻：每日固定觸發爬蟲批次的時間清單（24 小時制 (hour, minute)）。
# 24:00 以隔日 00:00 表示。同一日多次執行會覆蓋同一個 yyyy/mm/dd 資料夾。
DAILY_RUN_TIMES: Final[tuple[tuple[int, int], ...]] = (
    (8, 30),
    (15, 0),
    (16, 0),
    (17, 0),
    (18, 0),
    (19, 0),
    (20, 0),
    (21, 0),
    (22, 0),
    (23, 0),
    (0, 0),
)

# TWSE 有價證券清單（ISIN）來源 URL
# strMode=2 → 上市；strMode=4 → 上櫃。
# 多檔 ETF（特別是主動式）會持有上櫃股票（如 8299 群聯、5274 信驊、6261 鴻勁），
# 若只抓 strMode=2，抽抽樂頁面查不到代號與產業別。下方 tuple 內任一來源失敗，
# 其餘來源仍可正常合併寫入 symbol.json。
TWSE_SECURITIES_SOURCES: Final[tuple[tuple[str, str], ...]] = (
    ("上市", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"),
    ("上櫃", "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"),
)

# TWSE 證券清單每日觸發時刻：03:00 與 15:00，每次執行覆蓋 symbol.{json,csv}
TWSE_SECURITIES_RUN_TIMES: Final[tuple[tuple[int, int], ...]] = (
    (3, 0),
    (15, 0),
)
