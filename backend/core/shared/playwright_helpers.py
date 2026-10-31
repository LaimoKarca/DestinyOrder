# -*- coding: utf-8-sig -*-
"""Playwright 通用操作 helper。

集中以下重複邏輯：

* :func:`headless_page` 上下文管理：自動開瀏覽器 / 收尾
* :func:`click_xpath`：點擊 XPath 並等待頁面渲染
* :func:`extract_text_by_xpath`：擷取單一 XPath 的文字
* :func:`extract_texts_by_xpath`：批次擷取多個 XPath

各 crawler 僅須描述自己的 URL、popup 處理與表格解析。
"""

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import (
    Browser,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from backend.core.shared.log_handler import get_logger

logger = get_logger(__name__)

_STATE_TIMEOUT: str = "等待元素逾時"
_STATE_NOT_FOUND: str = "未找到元素"
_STATE_EMPTY: str = "標籤內無文字"
_STATE_UNEXPECTED: str = "發生未預期錯誤"


@contextmanager
def headless_page() -> Iterator[Page]:
    """以無頭模式啟動 Chromium 並產生 Page，離開時自動收尾。

    Yields:
        已建立完成的 Page 物件。
    """
    with sync_playwright() as runtime:
        browser: Browser = runtime.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            yield page
        finally:
            browser.close()


def click_xpath(
    page: Page,
    xpath: str,
    timeout: int = 5000,
    settle_ms: int = 2000,
) -> bool:
    """點擊 XPath 對應元素並等待頁面渲染。

    Args:
        page: Playwright Page 實例。
        xpath: 目標元素的 XPath。
        timeout: 等待元素出現的超時（毫秒）。
        settle_ms: 點擊後額外等待頁面動態渲染的時間（毫秒）。

    Returns:
        成功點擊回傳 True；逾時或例外則回傳 False。
    """
    try:
        element = page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        if not element:
            return False
        element.click()
        page.wait_for_timeout(settle_ms)
        return True
    except PlaywrightTimeoutError:
        logger.warning("Timeout while clicking xpath: %s", xpath)
        return False
    except Exception as exc:
        logger.warning("Click failed on xpath %s: %s", xpath, exc)
        return False


def extract_text_by_xpath(page: Page, xpath: str, timeout: int = 3000) -> str:
    """擷取單一 XPath 節點的文字內容。

    Args:
        page: Playwright Page 實例。
        xpath: 目標元素的 XPath。
        timeout: 等待元素出現的超時（毫秒）。

    Returns:
        擷取到的文字，或對應失敗狀態的提示字串。
    """
    try:
        element = page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
        if not element:
            return _STATE_NOT_FOUND
        text = element.text_content()
        return text.strip() if text else _STATE_EMPTY
    except PlaywrightTimeoutError:
        return _STATE_TIMEOUT
    except Exception as exc:
        logger.warning("Extract failed on xpath %s: %s", xpath, exc)
        return _STATE_UNEXPECTED


def extract_texts_by_xpath(
    page: Page,
    xpaths: list[str],
    timeout: int = 3000,
) -> dict[str, str]:
    """批次擷取多個 XPath 節點的文字。

    Args:
        page: Playwright Page 實例。
        xpaths: XPath 字串列表。
        timeout: 每個元素等待出現的超時（毫秒）。

    Returns:
        以 XPath 為鍵、對應文字為值的字典。
    """
    return {xp: extract_text_by_xpath(page, xp, timeout=timeout) for xp in xpaths}
