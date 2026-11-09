# -*- coding: utf-8 -*-
"""Regression coverage for the 00981A official portfolio layout."""
import unittest

from backend.core.funds.crawlers.uni_00981a import (
    _parse_stock_rows,
    _validate_portfolio,
)

STOCK_HEADERS = ["股票代號", "股票名稱", "股數", "持股權重"]


class Uni00981aPortfolioTests(unittest.TestCase):
    def test_futures_table_is_not_an_equity_table(self):
        rows = [
            ["期貨(名目本金)"],
            ["期貨代號", "期貨名稱", "持股權重", "口數", "契約年月"],
            ["TX", "台指期貨", "2.83%", "867", "2026/11"],
        ]
        self.assertIsNone(_parse_stock_rows(rows))

    def test_equity_header_selects_weight_not_share_quantity(self):
        rows = [
            ["股票"],
            STOCK_HEADERS,
            ["2330", "台積電", "17,724,000", "15.58%"],
            ["2454", "聯發科", "5,712,000", "8.37%"],
        ]
        holdings = _parse_stock_rows(rows)
        self.assertEqual([(x.name, x.weight) for x in holdings], [
            ("台積電", "15.58%"), ("聯發科", "8.37%")
        ])

    def test_short_or_bad_portfolio_is_rejected(self):
        rows = [["股票"], STOCK_HEADERS] + [
            [str(2300 + i), f"股票{i}", "1000", "3.0%"] for i in range(10)
        ]
        holdings = _parse_stock_rows(rows)
        with self.assertRaises(ValueError):
            _validate_portfolio(holdings)

    def test_full_portfolio_with_plausible_weight_passes(self):
        rows = [["股票"], STOCK_HEADERS] + [
            [str(2300 + i), f"股票{i}", "1000", "3.0%"] for i in range(30)
        ]
        holdings = _parse_stock_rows(rows)
        self.assertEqual(len(holdings), 30)
        _validate_portfolio(holdings)

    def test_impossible_weight_is_rejected(self):
        rows = [["股票"], STOCK_HEADERS, ["2330", "台積電", "1", "867%"]]
        holdings = _parse_stock_rows(rows)
        with self.assertRaises(ValueError):
            _validate_portfolio(holdings)

    def test_duplicate_codes_are_rejected(self):
        rows = [["股票"], STOCK_HEADERS,
                ["2330", "台積電", "1", "3%"],
                ["2330", "台積電", "2", "3%"]]
        with self.assertRaises(ValueError):
            _parse_stock_rows(rows)


if __name__ == "__main__":
    unittest.main()
