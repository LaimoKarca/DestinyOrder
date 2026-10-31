# -*- coding: utf-8-sig -*-
"""專案根目錄 CLI 薄轉發層：將呼叫委派給 Canonical 實作 `backend.scripts.seed_demo_data`。

支援兩種啟動方式：
1. 本機直接執行：`python scripts/seed_demo_data.py`
2. 後端模組或容器內執行：`python -m backend.scripts.seed_demo_data`
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.scripts.seed_demo_data import (  # noqa: E402,F401
    DEMO_DATE_PARTS,
    DEMO_DATE_STR,
    DEMO_ETF_SNAPSHOTS,
    DEMO_SECURITIES,
    ENCODING,
    _commit_directory_noreplace,
    _default_target_dir,
    _ensure_no_symlink_in_hierarchy,
    _is_reparse_or_symlink,
    _safe_cleanup_staging,
    _write_staging_files,
    main,
    seed_demo_data,
)

if __name__ == "__main__":
    raise SystemExit(main())
