# -*- coding: utf-8-sig -*-
"""所有基金爬蟲的中央註冊表。

新增爬蟲時，在此檔末尾的 :data:`CRAWLERS` tuple 增加一筆 :class:`CrawlerEntry`
即可，orchestrator 與 scheduler 不需任何更動。
"""

from typing import Callable, Final, NamedTuple

from backend.core.funds.crawlers import (
    fubon_006208,
    kgi_009816,
    uni_00403a,
    uni_00981a,
    yuanta_0050,
)
from backend.schemas.stock_price import StockPriceSnapshot

FetchFn = Callable[[], StockPriceSnapshot | None]


class CrawlerEntry(NamedTuple):
    """單一基金爬蟲在註冊表中的條目。"""

    code: str
    name: str
    fetch: FetchFn
    source_url: str


CRAWLERS: Final[tuple[CrawlerEntry, ...]] = (
    CrawlerEntry(yuanta_0050.CODE, yuanta_0050.NAME, yuanta_0050.fetch, yuanta_0050.URL),
    CrawlerEntry(
        fubon_006208.CODE, fubon_006208.NAME, fubon_006208.fetch, fubon_006208.URL_PROFILE
    ),
    CrawlerEntry(kgi_009816.CODE, kgi_009816.NAME, kgi_009816.fetch, kgi_009816.URL),
    CrawlerEntry(uni_00403a.CODE, uni_00403a.NAME, uni_00403a.fetch, uni_00403a.URL),
    CrawlerEntry(uni_00981a.CODE, uni_00981a.NAME, uni_00981a.fetch, uni_00981a.URL),
)
