# -*- coding: utf-8-sig -*-
"""偵錯用 CLI：挑單一爬蟲跑一次，結果只印到 stdout，**不寫入** ``data/``。

定位：
    * **僅供偵錯 / 單元測試 / 維護用**。
    * 與 :mod:`backend.run_scheduler`（正式排程，落地到 ``data/funds/``）
      互不重疊，不會啟動排程、不會覆寫任何 JSON 檔。
    * 與各 crawler 檔尾的 ``__main__`` 區塊效果相同，差別是這支從註冊表查
      表，方便用單一指令依代碼挑檔。

用法（兩種啟動方式擇一，皆可）::

    # 1. 模組模式（建議，於專案根目錄執行）
    python -m backend.scripts.debug_crawler 0050
    python -m backend.scripts.debug_crawler 009816 > out.json

    # 2. 直接執行（VS Code「執行檔案」按鈕也可）
    python backend/scripts/debug_crawler.py 0050

不帶參數或代碼錯誤時，會列出所有已註冊的基金代碼。
"""

import sys
from pathlib import Path

# 直接以檔案路徑執行（python backend/scripts/debug_crawler.py ...）時，
# sys.path[0] 會是 backend/scripts/ 而非專案根目錄，導致 `import backend.*` 失敗。
# 將專案根目錄補進 sys.path 以兼容兩種啟動方式；以 `python -m` 啟動時為無害冗餘。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.funds._dev_runner import run_crawler_standalone  # noqa: E402
from backend.core.funds.registry import CRAWLERS  # noqa: E402


def _print_usage() -> None:
    """列印用法與所有已註冊的爬蟲代碼。"""
    print("Usage: python -m backend.scripts.debug_crawler <code>", file=sys.stderr)
    print("Registered crawlers:", file=sys.stderr)
    for entry in CRAWLERS:
        print(f"  {entry.code:<8} {entry.name}", file=sys.stderr)


def main() -> None:
    """CLI 進入點。"""
    if len(sys.argv) < 2:
        _print_usage()
        raise SystemExit(2)

    target_code = sys.argv[1].strip()
    entry = next((c for c in CRAWLERS if c.code == target_code), None)
    if entry is None:
        print(f"[ERROR] unknown crawler code: {target_code}", file=sys.stderr)
        _print_usage()
        raise SystemExit(2)

    run_crawler_standalone(entry.fetch, entry.code)


if __name__ == "__main__":
    main()
