# -*- coding: utf-8-sig -*-
"""每日基金狀態快照的 Pydantic schema。

未來 FastAPI 路由可直接以 :class:`StockPriceSnapshot` 作為 ``response_model``。
"""

from pydantic import BaseModel, ConfigDict, Field


class Holding(BaseModel):
    """單一持股明細。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="持股名稱")
    weight: str = Field(..., description="持股權重（已含 % 符號）")


class StockPriceSnapshot(BaseModel):
    """單一基金 / ETF 的單日快照。"""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="基金代碼，如 0050 / 00981A")
    name: str = Field(..., description="基金完整名稱")
    nav: str = Field(..., description="淨值（字串形式，保留原始小數位數）")
    change_percent: str = Field(..., description="漲跌幅，正規化後可能為 +1.23% / -0.61% 等")
    update_time: str = Field(..., description="資料日期 YYYY/MM/DD")
    holdings: list[Holding] = Field(default_factory=list, description="持股明細列表")
