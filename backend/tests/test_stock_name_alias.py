# -*- coding: utf-8-sig -*-
"""離線回歸測試：驗證 ETF 成分股跨投信名稱別名正規化（創意電子 -> 創意, 3443）。

執行方式（於專案根目錄）：
    .\\venv\\Scripts\\python.exe -B -m unittest discover -s backend/tests -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.funds import etf_aggregator, lucky_aggregator  # noqa: E402
from backend.core.shared.config import ENCODING  # noqa: E402


class StockNameAliasRegressionTest(unittest.TestCase):
    """使用合成離線 fixture 驗證『創意電子』(009816) 與『創意』(00403A/00981A/symbol.json) 之精確別名合併。"""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmpdir.name)
        self.symbol_file = self.base_dir / "symbol.json"
        self.dated_dir = self.base_dir / "2026" / "05" / "24"
        self.dated_dir.mkdir(parents=True, exist_ok=True)

        symbol_payload = {
            "updated_at": "2026-05-24T15:00:00",
            "count": 2,
            "data": [
                {"symbol": "2330", "name": "台積電", "industry": "半導體業"},
                {"symbol": "3443", "name": "創意", "industry": "半導體業"},
            ],
        }
        self.symbol_file.write_text(
            json.dumps(symbol_payload, ensure_ascii=False),
            encoding=ENCODING,
        )

        snapshots = {
            "009816": {
                "code": "009816",
                "name": "凱基台灣TOP50",
                "nav": "15.20",
                "change_percent": "+0.50%",
                "update_time": "2026/05/24",
                "holdings": [
                    {"name": "台積電", "weight": "42.00%"},
                    {"name": "創意電子", "weight": "1.04%"},
                ],
            },
            "00403A": {
                "code": "00403A",
                "name": "主動台新台灣優勢成長",
                "nav": "12.80",
                "change_percent": "+0.80%",
                "update_time": "2026/05/24",
                "holdings": [
                    {"name": "創意", "weight": "3.11%"},
                ],
            },
            "00981A": {
                "code": "00981A",
                "name": "主動統一台股增長",
                "nav": "13.50",
                "change_percent": "+0.95%",
                "update_time": "2026/05/24",
                "holdings": [
                    {"name": "創意*", "weight": "2.35%"},
                ],
            },
        }
        for code, payload in snapshots.items():
            (self.dated_dir / f"{code}.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding=ENCODING,
            )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_normalize_stock_name_maps_exact_alias_without_fuzzy_truncation(self) -> None:
        """_normalize_stock_name 應精確將『創意電子』轉為『創意』，且不得模糊截斷其他『*電子』名稱。"""
        self.assertEqual(lucky_aggregator._normalize_stock_name("創意電子"), "創意")
        self.assertEqual(lucky_aggregator._normalize_stock_name(" 創意電子* "), "創意")
        self.assertEqual(lucky_aggregator._normalize_stock_name("國巨*"), "國巨")
        # 確保不做模糊截字（不得把其他含「電子」字尾的公司截斷）
        self.assertEqual(lucky_aggregator._normalize_stock_name("台達電子"), "台達電子")
        self.assertEqual(lucky_aggregator._normalize_stock_name("聯華電子"), "聯華電子")
        self.assertEqual(lucky_aggregator._normalize_stock_name("環旭電子"), "環旭電子")

    def test_build_lucky_response_merges_creative_electronics_across_three_etfs(self) -> None:
        """離線 fixture：build_lucky_response 應直接依傳入 base 讀取 symbol.json 並合併為單一 3443 標的。"""
        resp = lucky_aggregator.build_lucky_response(base=self.base_dir)

        self.assertIsNotNone(resp)
        assert resp is not None
        self.assertEqual(resp.date, "2026/05/24")

        by_name = {stock.name: stock for stock in resp.stocks}
        self.assertNotIn("創意電子", by_name)
        self.assertIn("創意", by_name)
        self.assertEqual(len(resp.stocks), 2)

        creative = by_name["創意"]
        self.assertEqual(creative.symbol, "3443")
        self.assertEqual(creative.industry, "半導體業")
        self.assertEqual(
            [src.etf_code for src in creative.sources],
            ["009816", "00403A", "00981A"],
        )

    def test_build_by_etf_response_normalizes_009816_holding_and_populates_symbol_3443(self) -> None:
        """離線 fixture：build_by_etf_response 中 009816 持股應正規化為『創意』並補上 symbol 3443。"""
        resp = etf_aggregator.build_by_etf_response(base=self.base_dir)

        self.assertIsNotNone(resp)
        assert resp is not None
        self.assertEqual(resp.date, "2026/05/24")

        etf_009816 = next(e for e in resp.etfs if e.code == "009816")
        holdings_by_name = {h.name: h for h in etf_009816.holdings}
        self.assertNotIn("創意電子", holdings_by_name)
        self.assertIn("創意", holdings_by_name)
        self.assertEqual(holdings_by_name["創意"].symbol, "3443")
        self.assertEqual(holdings_by_name["創意"].weight, "1.04%")

    def test_isolated_base_without_symbol_file_does_not_leak_external_symbols(self) -> None:
        """當傳入之隔離 base 下無 symbol.json 時，不得回退讀取外部 FUNDS_DATA_ROOT/symbol.json。"""
        self.symbol_file.unlink()

        lucky_resp = lucky_aggregator.build_lucky_response(base=self.base_dir)
        self.assertIsNotNone(lucky_resp)
        assert lucky_resp is not None
        for stock in lucky_resp.stocks:
            self.assertIsNone(stock.symbol)
            self.assertIsNone(stock.industry)

        by_etf_resp = etf_aggregator.build_by_etf_response(base=self.base_dir)
        self.assertIsNotNone(by_etf_resp)
        assert by_etf_resp is not None
        for etf in by_etf_resp.etfs:
            for holding in etf.holdings:
                self.assertIsNone(holding.symbol)


if __name__ == "__main__":
    unittest.main()
