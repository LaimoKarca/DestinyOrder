# -*- coding: utf-8-sig -*-
"""抽抽樂 API 的回應 Schema。

把 5 檔 ETF 的成分股聚合成「可抽取股票池」，並補上 TWSE 證券清單中的
代號與產業別。前端 ``LuckyDraw`` 頁面 fetch ``/api/funds/latest`` 後即可
直接渲染與抽籤，不需再自行交叉比對。
"""

from pydantic import BaseModel, ConfigDict, Field


class DrawSource(BaseModel):
    """同一支股票在某檔 ETF 中的來源紀錄。"""

    model_config = ConfigDict(from_attributes=True)

    etf_code: str = Field(..., description="ETF 代號，如 0050 / 00981A")
    etf_name: str = Field(..., description="ETF 完整名稱")
    weight: str = Field(..., description="該股在此 ETF 內的權重（含 % 符號）")


class DrawableStock(BaseModel):
    """股票池中的單一可抽取標的。"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="股票名稱（已去除如 `*` 等狀態字尾）")
    symbol: str | None = Field(
        None, description="TWSE 證券代號；symbol.json 查無時為 None"
    )
    industry: str | None = Field(
        None, description="TWSE 公告的產業別；查無時為 None"
    )
    sources: list[DrawSource] = Field(
        default_factory=list, description="哪幾檔 ETF 持有此股，含個別權重"
    )


class FundsLuckyResponse(BaseModel):
    """抽抽樂頁面所需的當日彙整資料。"""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., description="基金資料日期資料夾相對路徑，如 2026/05/23")
    etf_codes: list[str] = Field(
        default_factory=list, description="此次回應實際包含的 ETF 代號列表"
    )
    stocks: list[DrawableStock] = Field(
        default_factory=list, description="可抽取股票池，依名稱排序"
    )
