# -*- coding: utf-8-sig -*-
"""DestinyOrder 後端 FastAPI 應用程式入口。

啟動方式（擇一，皆可於專案根目錄或 backend/ 目錄執行）::

    # 1. 直接執行（與 `cd backend && python main.py` 一致）
    python backend/main.py

    # 2. uvicorn CLI（reload 模式）
    uvicorn backend.main:app --reload

預設綁定 127.0.0.1:8000；前端 Vite dev server (5173) 透過 proxy 轉發
``/api/*`` 至本服務，故開發時不需處理 CORS。
"""

import os
import sys
from pathlib import Path

# 直接以檔案路徑執行（python backend/main.py 或 cd backend && python main.py）時，
# sys.path[0] 會是 backend/ 而非專案根目錄，導致 `import backend.*` 失敗。
# 將專案根目錄補進 sys.path 以兼容兩種啟動方式；以 `python -m` 啟動時為無害冗餘。
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from backend.core.shared.log_handler import get_logger  # noqa: E402
from backend.routers import funds as funds_router  # noqa: E402

logger = get_logger(__name__)

_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def _resolve_cors_origins() -> list[str]:
    raw = os.environ.get("DESTINYORDER_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="DestinyOrder API",
    description="台股 ETF 抽抽樂後端服務",
    version="0.1.0",
)

# 預設允許本機 Vite dev server (localhost / 127.0.0.1:5173) 直連，
# 可透過 DESTINYORDER_CORS_ORIGINS 環境變數（逗號分隔）自訂允許清單。
app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_cors_origins(),
    allow_methods=["GET"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(funds_router.router)


@app.get("/api/health", tags=["meta"])
def health_check() -> dict[str, str]:
    """簡易健康檢查端點。"""
    return {"status": "ok"}


def main() -> None:
    """以單 worker + reload 模式啟動 uvicorn（開發用）。"""
    import uvicorn

    host = os.environ.get("DESTINYORDER_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("DESTINYORDER_PORT", "8000"))
    logger.info("Starting DestinyOrder API on http://%s:%d", host, port)
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[str(_PROJECT_ROOT / "backend")],
    )


if __name__ == "__main__":
    main()
