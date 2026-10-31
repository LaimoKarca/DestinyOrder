# -*- coding: utf-8-sig -*-
"""JSON 寫入與日期分層目錄共用工具。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.shared.config import ENCODING


def save_json(data: Any, path: Path) -> None:
    """以專案統一編碼將資料覆寫成 JSON 檔。

    自動建立 ``path`` 的所有上層目錄。已存在的檔案會被無條件覆蓋。

    Args:
        data: 任何可被 ``json.dump`` 序列化的物件。
        path: 目標檔案路徑。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=ENCODING) as fp:
        json.dump(data, fp, ensure_ascii=False, indent=4)


def build_dated_dir(base: Path, moment: datetime | None = None) -> Path:
    """在 ``base`` 之下建立 ``yyyy/mm/dd`` 子目錄並回傳。

    Args:
        base: 基底資料夾。
        moment: 指定時間，未提供則使用系統當下時間。

    Returns:
        已存在（必要時遞迴建立）的子目錄路徑。
    """
    when = moment or datetime.now()
    target = base / f"{when.year:04d}" / f"{when.month:02d}" / f"{when.day:02d}"
    target.mkdir(parents=True, exist_ok=True)
    return target
