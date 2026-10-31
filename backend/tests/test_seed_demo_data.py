# -*- coding: utf-8-sig -*-
"""合成示範資料產生器 (backend/scripts/seed_demo_data.py 與 scripts/seed_demo_data.py wrapper) 單元與安全回歸測試。

涵蓋：
1. 所有內建 `DEMO_ETF_SNAPSHOTS` 常數皆通過 `StockPriceSnapshot.model_validate` 嚴格驗證，
   且於新目標路徑原子建立後可直接被 `build_lucky_response` 與 `build_by_etf_response` 聚合。
2. 目標目錄已存在（含既有檔案）時必須拒絕寫入（拋出 FileExistsError 並保留既有檔案不變）。
3. 目標路徑為 symlink / reparse point 時必須拒絕寫入。
4. 單次原子 `os.rename` 失敗時必須完整清理暫存目錄 `.destinyorder_demo_seed_*`，且不殘留半套檔案。
5. 若暫存期間目標路徑出現外部並行寫入之 sentinel 檔案，commit 前必須拒絕覆寫並完整保留該外部 sentinel。
6. `config.resolve_configured_path` 與 `seed_demo_data._default_target_dir` 空字串/空白回退預設與相對路徑相對於 `PROJECT_ROOT` 解析。
"""

from __future__ import annotations

import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend.core.funds.etf_aggregator import build_by_etf_response
from backend.core.funds.lucky_aggregator import build_lucky_response
from backend.core.shared import config as shared_config
from backend.schemas.stock_price import StockPriceSnapshot
from backend.scripts import seed_demo_data as seed_mod
from backend.scripts.seed_demo_data import (
    DEMO_DATE_STR,
    DEMO_ETF_SNAPSHOTS,
    seed_demo_data,
)
from scripts import seed_demo_data as root_wrapper_mod


class SeedDemoDataTest(unittest.TestCase):
    """驗證合成示範資料產生器的 Schema 合規性、聚合正確性與原子安全保護邊界。"""

    def test_demo_snapshots_match_strict_schema_and_aggregate_successfully(self) -> None:
        """所有合成快照常數須通過 StockPriceSnapshot 嚴格驗證，且聚合器回傳 6 檔無 null symbol 之示範標的。"""
        self.assertIs(root_wrapper_mod.seed_demo_data, seed_demo_data)
        for raw_snapshot in DEMO_ETF_SNAPSHOTS:
            validated = StockPriceSnapshot.model_validate(raw_snapshot)
            self.assertEqual(validated.update_time, DEMO_DATE_STR)
            self.assertTrue(len(validated.holdings) > 0)

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "funds_demo"
            written = seed_demo_data(target)
            self.assertEqual(written, target.resolve())
            self.assertTrue((target / "symbol.json").is_file())
            self.assertTrue((target / "symbol.csv").is_file())
            self.assertTrue((target / "2000" / "01" / "03" / "0050.json").is_file())

            lucky = build_lucky_response(base=target)
            self.assertIsNotNone(lucky)
            assert lucky is not None
            self.assertEqual(lucky.date, DEMO_DATE_STR)
            self.assertEqual(
                lucky.etf_codes,
                ["0050", "006208", "009816", "00403A", "00981A"],
            )
            self.assertEqual(len(lucky.stocks), 6)
            for stock in lucky.stocks:
                self.assertIn("示範", stock.name)
                self.assertIsNotNone(stock.symbol)
                assert stock.symbol is not None
                self.assertTrue(stock.symbol.startswith("DEMO"))

            by_etf = build_by_etf_response(base=target)
            self.assertIsNotNone(by_etf)
            assert by_etf is not None
            self.assertEqual(by_etf.date, DEMO_DATE_STR)
            self.assertEqual(len(by_etf.etfs), 5)

    def test_refuses_existing_target_directory_without_modifying_sentinel(self) -> None:
        """既有目錄必須拒絕寫入，且原有 sentinel 檔案內容不可被更動或刪除。"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing_funds"
            target.mkdir()
            sentinel = target / "existing.json"
            sentinel.write_text('{"keep": true}', encoding="utf-8")

            with self.assertRaises(FileExistsError):
                seed_demo_data(target)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), '{"keep": true}')
            self.assertEqual(list(target.iterdir()), [sentinel])

    def test_refuses_symlink_or_reparse_target(self) -> None:
        """若目標路徑或其父路徑為 symlink / reparse point，必須拒絕寫入。"""
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = Path(tmp) / "real_target"
            real_dir.mkdir()
            link_dir = Path(tmp) / "symlink_target"

            symlink_created = False
            try:
                os.symlink(real_dir, link_dir, target_is_directory=True)
                symlink_created = True
            except (OSError, NotImplementedError):
                symlink_created = False

            if symlink_created:
                with self.assertRaises(ValueError):
                    seed_demo_data(link_dir)
            else:
                with mock.patch(
                    "backend.scripts.seed_demo_data._is_reparse_or_symlink",
                    side_effect=lambda p: Path(p) == link_dir.resolve(),
                ):
                    with self.assertRaises(ValueError):
                        seed_demo_data(link_dir)

            self.assertEqual(list(real_dir.iterdir()), [])

    def test_atomic_rollback_cleans_up_staging_when_commit_fails(self) -> None:
        """若 _commit_directory_noreplace 發生例外，必須清理同父目錄之暫存資料夾且不殘留半套檔案。"""
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            target = parent / "rollback_target"

            with mock.patch(
                "backend.scripts.seed_demo_data._commit_directory_noreplace",
                side_effect=OSError("simulated commit failure"),
            ):
                with self.assertRaises(OSError):
                    seed_demo_data(target)

            self.assertFalse(target.exists())
            self.assertEqual(list(parent.iterdir()), [])

    def test_preserves_external_sentinel_created_concurrently_before_commit(self) -> None:
        """若暫存寫入期間目標路徑被外部並行建立並寫入 sentinel，commit 前必須拒絕且完整保留外部 sentinel。"""
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            target = parent / "concurrent_target"
            orig_write = seed_mod._write_staging_files

            def _write_and_simulate_concurrent_target(staging_root: Path) -> None:
                orig_write(staging_root)
                target.mkdir(parents=True, exist_ok=True)
                (target / "concurrent_sentinel.json").write_text(
                    '{"external": "must_survive"}',
                    encoding="utf-8",
                )

            with mock.patch(
                "backend.scripts.seed_demo_data._write_staging_files",
                side_effect=_write_and_simulate_concurrent_target,
            ):
                with self.assertRaises(FileExistsError):
                    seed_demo_data(target)

            sentinel_path = target / "concurrent_sentinel.json"
            self.assertTrue(sentinel_path.is_file())
            self.assertEqual(
                sentinel_path.read_text(encoding="utf-8"),
                '{"external": "must_survive"}',
            )
            self.assertEqual(list(target.iterdir()), [sentinel_path])
            self.assertEqual(list(parent.iterdir()), [target])

    def test_resolve_configured_path_handles_empty_whitespace_and_relative_paths(self) -> None:
        """驗證環境變數為空字串/純空白時回退至預設值（不指到 cwd），且相對路徑固定相對於 PROJECT_ROOT。"""
        default_dir = shared_config.BACKEND_ROOT / "data"
        fake_root = Path(tempfile.gettempdir()).resolve() / "destinyorder_proj_root"

        with mock.patch.dict(
            os.environ,
            {
                "TEST_EMPTY_PATH": "",
                "TEST_SPACE_PATH": "   ",
                "TEST_REL_PATH": "custom_data/funds",
                "DESTINYORDER_FUNDS_DATA_ROOT": "   ",
                "DESTINYORDER_DATA_ROOT": "",
            },
            clear=False,
        ):
            self.assertEqual(
                shared_config.resolve_configured_path(
                    "TEST_EMPTY_PATH", default_dir, base_root=fake_root
                ),
                default_dir.resolve(),
            )
            self.assertEqual(
                shared_config.resolve_configured_path(
                    "TEST_SPACE_PATH", default_dir, base_root=fake_root
                ),
                default_dir.resolve(),
            )
            self.assertEqual(
                shared_config.resolve_configured_path(
                    "TEST_REL_PATH", default_dir, base_root=fake_root
                ),
                (fake_root / "custom_data" / "funds").resolve(),
            )
            self.assertEqual(
                seed_mod._default_target_dir().resolve(),
                (shared_config.BACKEND_ROOT / "data" / "funds").resolve(),
            )

    def test_refuses_existing_or_concurrent_empty_target_directory(self) -> None:
        """驗證已存在之空目錄及 commit 階段並行出現之空目錄皆被拒絕且保留原狀。"""
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            existing_empty = parent / "existing_empty"
            existing_empty.mkdir()

            with self.assertRaises(FileExistsError):
                seed_demo_data(existing_empty)
            self.assertTrue(existing_empty.is_dir())
            self.assertEqual(list(existing_empty.iterdir()), [])

            # 模擬通過 commit 前 exists() 檢查後、進入 _commit_directory_noreplace 前一刻出現並行空目錄
            race_empty = parent / "race_empty"
            orig_commit = seed_mod._commit_directory_noreplace

            def _create_empty_then_commit(staging: Path, dst: Path) -> None:
                dst.mkdir(parents=True, exist_ok=True)
                orig_commit(staging, dst)

            with mock.patch(
                "backend.scripts.seed_demo_data._commit_directory_noreplace",
                side_effect=_create_empty_then_commit,
            ):
                with self.assertRaises(FileExistsError):
                    seed_demo_data(race_empty)

            self.assertTrue(race_empty.is_dir())
            self.assertEqual(list(race_empty.iterdir()), [])
            self.assertEqual(
                sorted(p.name for p in parent.iterdir()),
                ["existing_empty", "race_empty"],
            )

    def test_commit_directory_noreplace_linux_renameat2_and_unsupported_os_fail_closed(
        self,
    ) -> None:
        """驗證 Linux renameat2(RENAME_NOREPLACE) EEXIST/ENOSYS 與未支援 OS 均 fail closed，絕不 fallback 普通 rename。"""
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            src = parent / "src_dir"
            dst = parent / "dst_dir"
            src.mkdir()

            # 1) 未支援作業系統（例如 darwin）必須直接拋出 RuntimeError，不呼叫 os.rename
            with (
                mock.patch.object(seed_mod.sys, "platform", "darwin"),
                mock.patch("backend.scripts.seed_demo_data.os.rename") as mock_rename,
            ):
                with self.assertRaises(RuntimeError):
                    seed_mod._commit_directory_noreplace(src, dst)
                mock_rename.assert_not_called()

            # 2) Linux 下 libc 無 renameat2 符號時必須 fail closed (RuntimeError)
            fake_libc_missing = object()
            with (
                mock.patch.object(seed_mod.sys, "platform", "linux"),
                mock.patch(
                    "backend.scripts.seed_demo_data.ctypes.CDLL",
                    return_value=fake_libc_missing,
                ),
                mock.patch("backend.scripts.seed_demo_data.os.rename") as mock_rename,
            ):
                with self.assertRaises(RuntimeError):
                    seed_mod._commit_directory_noreplace(src, dst)
                mock_rename.assert_not_called()

            # 3) Linux 下 renameat2 回傳 EEXIST 時必須轉為 FileExistsError，且參數符合 AT_FDCWD=-100, RENAME_NOREPLACE=1
            fake_renameat2 = mock.MagicMock(return_value=-1)
            fake_libc = mock.MagicMock()
            fake_libc.renameat2 = fake_renameat2
            with (
                mock.patch.object(seed_mod.sys, "platform", "linux"),
                mock.patch(
                    "backend.scripts.seed_demo_data.ctypes.CDLL",
                    return_value=fake_libc,
                ),
                mock.patch(
                    "backend.scripts.seed_demo_data.ctypes.get_errno",
                    return_value=errno.EEXIST,
                ),
                mock.patch("backend.scripts.seed_demo_data.os.rename") as mock_rename,
            ):
                with self.assertRaises(FileExistsError):
                    seed_mod._commit_directory_noreplace(src, dst)
                mock_rename.assert_not_called()
                fake_renameat2.assert_called_once_with(
                    -100,
                    os.fsencode(str(src)),
                    -100,
                    os.fsencode(str(dst)),
                    1,
                )

            # 4) Linux 下檔案系統不支援 RENAME_NOREPLACE (EINVAL / ENOSYS) 時必須 fail closed (RuntimeError)
            with (
                mock.patch.object(seed_mod.sys, "platform", "linux"),
                mock.patch(
                    "backend.scripts.seed_demo_data.ctypes.CDLL",
                    return_value=fake_libc,
                ),
                mock.patch(
                    "backend.scripts.seed_demo_data.ctypes.get_errno",
                    return_value=errno.EINVAL,
                ),
                mock.patch("backend.scripts.seed_demo_data.os.rename") as mock_rename,
            ):
                with self.assertRaises(RuntimeError):
                    seed_mod._commit_directory_noreplace(src, dst)
                mock_rename.assert_not_called()


if __name__ == "__main__":
    unittest.main()
