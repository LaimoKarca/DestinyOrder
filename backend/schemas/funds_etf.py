# -*- coding: utf-8-sig -*-
"""權重查詢 API 的回應 Schema。

按 ETF 分組回傳成分股明細，每檔 ETF 含：
- 基本資料（代號、名稱、更新日期、官方來源網址）
- 持股明細（含 TWSE 補上的證券代號）

前端 ``WeightsView`` 頁面 fetch ``/api/funds/by_etf`` 後可直接切換不同
ETF 顯示其持股表，不需自己交叉比對。
"""

from pydantic import BaseModel, ConfigDict, Field


class EtfHolding(BaseModel):
    """ETF 持股明細（含補齊的 TWSE 證券代號）。"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="股票名稱（已去除如 `*` 等狀態字尾）")
    symbol: str | None = Field(
        None, description="TWSE 證券代號；symbol.json 查無時為 None"
    )
    weight: str = Field(..., description="該股在此 ETF 內的權重（含 % 符號）")


class EtfDetail(BaseModel):
    """單一 ETF 的完整成分股明細。"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="ETF 代號")
    name: str = Field(..., description="ETF 完整名稱")
    update_time: str = Field(..., description="該檔 ETF 自身公告的資料日期")
    source_url: str = Field(..., description="該檔 ETF 的官方資料來源網址")
    holdings: list[EtfHolding] = Field(
        default_factory=list, description="持股明細（依原始順序保留，通常為權重由大到小）"
    )


class FundsByEtfResponse(BaseModel):
    """權重查詢 API 回應。"""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., description="資料夾日期相對路徑，如 2026/05/23")
    etfs: list[EtfDetail] = Field(
        default_factory=list, description="所有 ETF 的明細，依註冊順序排列"
    )
