# -*- coding: utf-8 -*-
"""Regression tests for 00403A's changing portfolio page."""
import unittest
from unittest.mock import patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from backend.core.funds.crawlers.uni_00403a import (
    _parse_stock_rows,
    _validate_holdings,
    fetch,
)

HEADERS = ["股票代號", "股票名稱", "股數", "持股權重"]


class Uni00403aPortfolioTests(unittest.TestCase):
    def test_stock_table_uses_weight_not_shares(self):
        rows = [["股票"], HEADERS, ["2330", "台積電", "8,250,000", "16%"],
                ["2454", "聯發科", "1,000,000", "5.56%"]]
        value = _parse_stock_rows(rows)
        self.assertEqual([(x.name, x.weight) for x in value], [
            ("台積電", "16%"), ("聯發科", "5.56%")])

    def test_summary_and_futures_are_not_stock_tables(self):
        self.assertIsNone(_parse_stock_rows([
            ["項目", "金額", "權重"],
            ["股票", "NTD 100000", "83%"],
        ]))
        self.assertIsNone(_parse_stock_rows([
            ["期貨"], ["期貨代號", "期貨名稱", "持股權重", "口數"],
            ["TX", "台指期貨", "2%", "867"],
        ]))

    def test_short_holding_list_cannot_be_published(self):
        few = _parse_stock_rows([["股票"], HEADERS] + [
            [str(2300 + i), f"股票{i}", "1000", "5%"] for i in range(10)
        ])
        with self.assertRaises(ValueError):
            _validate_holdings(few)

    def test_valid_full_holding_list(self):
        full = _parse_stock_rows([["股票"], HEADERS] + [
            [str(2300 + i), f"股票{i}", "1000", "3%"] for i in range(30)
        ])
        self.assertEqual(_validate_holdings(full), 90.0)

    def test_reject_impossible_weight(self):
        holdings = _parse_stock_rows([
            ["股票"], HEADERS, ["2330", "台積電", "1000", "867%"]
        ])
        with self.assertRaises(ValueError):
            _validate_holdings(holdings)

    def test_reject_duplicate_stock_codes(self):
        with self.assertRaises(ValueError):
            _parse_stock_rows([["股票"], HEADERS,
                               ["2330", "台積電", "1000", "16%"],
                               ["2330", "台積電", "1000", "16%"]])

    def test_transient_timeout_retries_once(self):
        fake_snapshot = object()
        with patch("backend.core.funds.crawlers.uni_00403a._fetch_once",
                   side_effect=[PlaywrightTimeoutError("timeout"), fake_snapshot]) as call:
            self.assertIs(fetch(), fake_snapshot)
            self.assertEqual(call.call_count, 2)

    def test_two_timeouts_return_none(self):
        with patch("backend.core.funds.crawlers.uni_00403a._fetch_once",
                   side_effect=PlaywrightTimeoutError("timeout")) as call:
            self.assertIsNone(fetch())
            self.assertEqual(call.call_count, 2)


if __name__ == "__main__":
    unittest.main()
