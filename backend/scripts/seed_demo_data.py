# -*- coding: utf-8-sig -*-
"""DestinyOrder 合成示範資料產生器（純 Python 標準庫，Canonical 實作）。

用途：
- 為新 clone 的開源開發環境或首次初始化的容器資料卷產生最小可運行的合成示範資料（Synthetic Demo Seed），
  使後端 `/api/funds/latest`、`/api/funds/by_etf` 與前端 6 個路由在無真實爬蟲資料時
  即可完整體驗與執行測試。
- 嚴格採用固定歷史示範日期 `2000/01/03`、虛構代號 `DEMO1`～`DEMO6` 與名稱含「示範」
  之虛構公司，避免與真實台股上市櫃公司混淆，亦避免未來日期優先蓋過真實資料。
- 產出之每份 ETF 快照完全符合 `backend.schemas.stock_price.StockPriceSnapshot`
  嚴格 Schema（`extra="forbid"`，含 `code`、`name`、`nav`、`change_percent`、
  `update_time` 與 `holdings: [{name, weight}]` 百分比字串）。

安全保護：
1. 絕不讀取任何既有 `backend/data` 真實檔案，資料完全由程式內建常數合成。
2. 拒絕任何 symlink 或 Windows reparse point（含目標路徑及其現存父目錄）。
3. 嚴格拒絕任何已存在之目標路徑（含既有非空目錄、既有空目錄或檔案），絕不刪除或覆寫目標路徑內任何既有或並行產生之檔案。
4. 單次原子目錄提交與安全回滾：於目標同父目錄下建立專屬暫存目錄（`.destinyorder_demo_seed_*`），
   完整寫入並通過檢查後，於 commit 前重查目標路徑不存在且無 reparse point，再以單次 `os.rename(staging_dir, abs_target)`
   原子提交；若失敗，僅清理經同父目錄、前綴與非 reparse 驗證之本次 `staging_dir`，絕不觸碰 `abs_target`。
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Final

ENCODING: Final[str] = "utf-8-sig"
DEMO_DATE_PARTS: Final[tuple[str, str, str]] = ("2000", "01", "03")
DEMO_DATE_STR: Final[str] = "2000/01/03"
_STAGING_PREFIX: Final[str] = ".destinyorder_demo_seed_"
_FILE_ATTRIBUTE_REPARSE_POINT: Final[int] = 0x400
_LINUX_AT_FDCWD: Final[int] = -100
_LINUX_RENAME_NOREPLACE: Final[int] = 1

DEMO_SECURITIES: Final[tuple[dict[str, str], ...]] = (
    {
        "symbol": "DEMO1",
        "name": "示範半導體",
        "isin": "TWDEMO000011",
        "listed_date": "2000/01/03",
        "market": "上市(合成示範)",
        "industry": "示範科技業",
        "cfi": "ESVUFR",
    },
    {
        "symbol": "DEMO2",
        "name": "示範金控",
        "isin": "TWDEMO000029",
        "listed_date": "2000/01/03",
        "market": "上市(合成示範)",
        "industry": "示範金融業",
        "cfi": "ESVUFR",
    },
    {
        "symbol": "DEMO3",
        "name": "示範電信",
        "isin": "TWDEMO000037",
        "listed_date": "2000/01/03",
        "market": "上市(合成示範)",
        "industry": "示範通信網路業",
        "cfi": "ESVUFR",
    },
    {
        "symbol": "DEMO4",
        "name": "示範航運",
        "isin": "TWDEMO000045",
        "listed_date": "2000/01/03",
        "market": "上市(合成示範)",
        "industry": "示範航運業",
        "cfi": "ESVUFR",
    },
    {
        "symbol": "DEMO5",
        "name": "示範生技",
        "isin": "TWDEMO000052",
        "listed_date": "2000/01/03",
        "market": "上櫃(合成示範)",
        "industry": "示範生技醫療業",
        "cfi": "ESVUFR",
    },
    {
        "symbol": "DEMO6",
        "name": "示範精密",
        "isin": "TWDEMO000060",
        "listed_date": "2000/01/03",
        "market": "上市(合成示範)",
        "industry": "示範電子零組件業",
        "cfi": "ESVUFR",
    },
)

DEMO_ETF_SNAPSHOTS: Final[tuple[dict[str, Any], ...]] = (
    {
        "code": "0050",
        "name": "元大台灣50（合成示範資料）",
        "nav": "100.00",
        "change_percent": "+0.00%",
        "update_time": DEMO_DATE_STR,
        "holdings": [
            {"name": "示範半導體", "weight": "45.20%"},
            {"name": "示範金控", "weight": "20.50%"},
            {"name": "示範電信", "weight": "15.30%"},
            {"name": "示範航運", "weight": "11.00%"},
            {"name": "示範精密", "weight": "8.00%"},
        ],
    },
    {
        "code": "006208",
        "name": "富邦台50（合成示範資料）",
        "nav": "100.00",
        "change_percent": "+0.00%",
        "update_time": DEMO_DATE_STR,
        "holdings": [
            {"name": "示範半導體", "weight": "44.80%"},
            {"name": "示範金控", "weight": "21.00%"},
            {"name": "示範電信", "weight": "15.20%"},
            {"name": "示範航運", "weight": "10.50%"},
            {"name": "示範精密", "weight": "8.50%"},
        ],
    },
    {
        "code": "009816",
        "name": "凱基台灣TOP50（合成示範資料）",
        "nav": "10.00",
        "change_percent": "+0.00%",
        "update_time": DEMO_DATE_STR,
        "holdings": [
            {"name": "示範半導體", "weight": "32.00%"},
            {"name": "示範金控", "weight": "24.00%"},
            {"name": "示範電信", "weight": "18.00%"},
            {"name": "示範生技", "weight": "14.00%"},
            {"name": "示範精密", "weight": "12.00%"},
        ],
    },
    {
        "code": "00403A",
        "name": "主動統一台股升級50（合成示範資料）",
        "nav": "10.00",
        "change_percent": "+0.00%",
        "update_time": DEMO_DATE_STR,
        "holdings": [
            {"name": "示範半導體", "weight": "28.50%"},
            {"name": "示範生技", "weight": "26.50%"},
            {"name": "示範精密", "weight": "25.00%"},
            {"name": "示範航運", "weight": "20.00%"},
        ],
    },
    {
        "code": "00981A",
        "name": "主動統一台股增長（合成示範資料）",
        "nav": "10.00",
        "change_percent": "+0.00%",
        "update_time": DEMO_DATE_STR,
        "holdings": [
            {"name": "示範半導體", "weight": "30.00%"},
            {"name": "示範生技", "weight": "28.00%"},
            {"name": "示範精密", "weight": "22.00%"},
            {"name": "示範金控", "weight": "20.00%"},
        ],
    },
)


def _is_reparse_or_symlink(path: Path) -> bool:
    """檢查單一基礎路徑是否為 symlink 或 Windows reparse point / junction。"""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    if stat.S_ISLNK(st.st_mode):
        return True
    file_attrs = getattr(st, "st_file_attributes", 0)
    if file_attrs & _FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return False


def _ensure_no_symlink_in_hierarchy(target_dir: Path) -> None:
    """檢查 target_dir 本身及其所有已存在之父目錄，拒絕任何 symlink / reparse point。"""
    current = Path(os.path.abspath(str(target_dir)))
    for candidate in (current, *current.parents):
        if _is_reparse_or_symlink(candidate):
            raise ValueError(
                f"拒絕寫入：路徑或其父目錄包含 symlink / reparse point：{candidate}"
            )


def _default_target_dir() -> Path:
    """計算預設目標目錄（檔案位於 `<repo>/backend/scripts/seed_demo_data.py`，故 `parents[2]` 為 `<repo>`）。"""
    backend_root = Path(__file__).resolve().parents[1]
    repo_root = backend_root.parent
    env_override = os.environ.get("DESTINYORDER_FUNDS_DATA_ROOT", "").strip()
    if env_override:
        candidate = Path(env_override)
        return candidate if candidate.is_absolute() else (repo_root / candidate)
    data_override = os.environ.get("DESTINYORDER_DATA_ROOT", "").strip()
    if data_override:
        data_candidate = Path(data_override)
        data_root = (
            data_candidate
            if data_candidate.is_absolute()
            else (repo_root / data_candidate)
        )
        return data_root / "funds"
    return backend_root / "data" / "funds"


def _write_staging_files(staging_root: Path) -> None:
    """在暫存目錄內完整生成合成示範資料檔案。"""
    symbol_payload = {
        "updated_at": f"{DEMO_DATE_STR} 00:00:00",
        "count": len(DEMO_SECURITIES),
        "data": list(DEMO_SECURITIES),
    }
    (staging_root / "symbol.json").write_text(
        json.dumps(symbol_payload, ensure_ascii=False, indent=2),
        encoding=ENCODING,
    )

    csv_path = staging_root / "symbol.csv"
    fieldnames = ["symbol", "name", "isin", "listed_date", "market", "industry", "cfi"]
    with csv_path.open("w", encoding=ENCODING, newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in DEMO_SECURITIES:
            writer.writerow(row)

    dated_dir = staging_root.joinpath(*DEMO_DATE_PARTS)
    dated_dir.mkdir(parents=True, exist_ok=True)
    for snapshot in DEMO_ETF_SNAPSHOTS:
        out_path = dated_dir / f"{snapshot['code']}.json"
        out_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding=ENCODING,
        )


def _safe_cleanup_staging(staging_dir: Path, expected_parent: Path) -> None:
    """僅清理由本次建立、位於同一父目錄、具專屬前綴且非 reparse point 之暫存目錄。"""
    try:
        if not staging_dir.exists() and not _is_reparse_or_symlink(staging_dir):
            return
        if staging_dir.parent != expected_parent:
            return
        if not staging_dir.name.startswith(_STAGING_PREFIX):
            return
        if _is_reparse_or_symlink(staging_dir):
            return
        shutil.rmtree(staging_dir, ignore_errors=True)
    except OSError:
        pass


def _commit_directory_noreplace(staging_dir: Path, abs_target: Path) -> None:
    """以不覆寫既有目錄（含並行出現之空目錄）之原子操作提交暫存目錄。

    - Windows (`win32`)：原生 `os.rename` 對已存在之目標目錄（含空目錄）必定拋出 `FileExistsError`。
    - Linux (`linux*`)：標準 POSIX `rename(2)` 會替換已存在之空目錄，故透過 `ctypes` 呼叫
      `libc.renameat2(AT_FDCWD, src, AT_FDCWD, dst, RENAME_NOREPLACE=1)`；若目標已存在（`EEXIST`）
      則拋出 `FileExistsError`，若函式或檔案系統不支援則 fail closed（拋出 `RuntimeError`），絕不退回普通 `rename`。
    - 其他作業系統：未驗證目錄級 `RENAME_NOREPLACE`，一律 fail closed（拋出 `RuntimeError`）。
    """
    if sys.platform == "win32":
        os.rename(str(staging_dir), str(abs_target))
        return

    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise RuntimeError(
                "拒絕提交：目前 Linux libc 不支援 renameat2，無法保證 RENAME_NOREPLACE 原子不覆寫。"
            )
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        ctypes.set_errno(0)
        rc = renameat2(
            _LINUX_AT_FDCWD,
            os.fsencode(str(staging_dir)),
            _LINUX_AT_FDCWD,
            os.fsencode(str(abs_target)),
            _LINUX_RENAME_NOREPLACE,
        )
        if rc != 0:
            err = ctypes.get_errno()
            if err == errno.EEXIST:
                raise FileExistsError(
                    err,
                    os.strerror(err),
                    str(staging_dir),
                    None,
                    str(abs_target),
                )
            if err in (
                errno.EINVAL,
                errno.ENOSYS,
                getattr(errno, "EOPNOTSUPP", 95),
            ):
                raise RuntimeError(
                    f"拒絕提交：目前 Linux 核心或檔案系統不支援 renameat2(RENAME_NOREPLACE) (errno={err})，已安全中止。"
                )
            raise OSError(
                err or errno.EIO,
                os.strerror(err or errno.EIO),
                str(staging_dir),
                None,
                str(abs_target),
            )
        return

    raise RuntimeError(
        f"拒絕提交：目前作業系統 ({sys.platform}) 未驗證目錄級 RENAME_NOREPLACE 原子不覆寫支援（僅支援 Windows 與 Linux）。"
    )


def seed_demo_data(target_dir: Path | None = None) -> Path:
    """透過同父目錄暫存與單次原子 rename 建立合成示範資料目錄。

    Args:
        target_dir: 目標 funds 資料夾路徑（預設為 `DESTINYORDER_FUNDS_DATA_ROOT` 或 `backend/data/funds`）。
                    目標路徑必須尚不存在（若已存在任何目錄或檔案將拒絕寫入）。

    Returns:
        寫入完成之目標目錄絕對路徑。

    Raises:
        ValueError: 當目標路徑或父目錄含 symlink / reparse point 時。
        FileExistsError: 當目標路徑已存在（含非空目錄、空目錄或檔案），或於 commit 前被外部建立時。
    """
    raw_target = target_dir if target_dir is not None else _default_target_dir()
    _ensure_no_symlink_in_hierarchy(raw_target)
    abs_target = Path(os.path.abspath(str(raw_target)))

    if abs_target.exists() or _is_reparse_or_symlink(abs_target):
        raise FileExistsError(
            f"拒絕寫入：目標路徑已存在（為保護既有資料，僅允許於尚不存在之目標路徑原子建立）：{abs_target}"
        )

    parent_dir = abs_target.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    _ensure_no_symlink_in_hierarchy(abs_target)

    staging_dir = Path(
        tempfile.mkdtemp(prefix=_STAGING_PREFIX, dir=str(parent_dir))
    )
    try:
        _write_staging_files(staging_dir)

        # Commit 前重查：確保父目錄與暫存目錄未被置換為 symlink/reparse，且目標路徑仍不存在
        _ensure_no_symlink_in_hierarchy(abs_target)
        if _is_reparse_or_symlink(staging_dir):
            raise ValueError(f"拒絕提交：暫存目錄疑似遭置換為 reparse point：{staging_dir}")
        if abs_target.exists() or _is_reparse_or_symlink(abs_target):
            raise FileExistsError(
                f"拒絕提交：目標路徑於暫存期間已被外部建立，保留外部內容不覆寫：{abs_target}"
            )

        _commit_directory_noreplace(staging_dir, abs_target)
    finally:
        # 若單次原子提交成功，staging_dir 已不存在；若中途失敗，僅清理 staging_dir，絕不觸碰 abs_target
        _safe_cleanup_staging(staging_dir, parent_dir)

    return abs_target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="產生 DestinyOrder 合成示範資料（透過單次原子 rename 建立新目標資料夾）。"
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=None,
        help="目標 funds 資料夾路徑（預設讀取 DESTINYORDER_FUNDS_DATA_ROOT 或 backend/data/funds，該路徑必須尚不存在）。",
    )
    args = parser.parse_args(argv)

    try:
        written = seed_demo_data(args.target_dir)
    except (ValueError, FileExistsError, OSError) as exc:
        print(f"[seed_demo_data] 失敗：{exc}", file=sys.stderr)
        return 1

    print(
        f"[seed_demo_data] 已於 {written} 產生合成示範資料（示範日期 {DEMO_DATE_STR}，共 {len(DEMO_SECURITIES)} 檔合成示範標的）。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
