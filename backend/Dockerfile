# syntax=docker/dockerfile:1.7

# DestinyOrder 後端統一 image：同一份 image 由 docker-compose 以不同 command
# 啟動三個 service（API / 每日股價爬蟲 / TWSE 證券清單爬蟲）。
FROM python:3.11-slim

# Python 執行環境：不寫 .pyc、stdout/stderr 不緩衝（log 即時可見）、預設 UTF-8
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TZ=Asia/Taipei

# 系統層相依：
#   - tzdata：排程依賴本地時間（DAILY_RUN_TIMES / TWSE_SECURITIES_RUN_TIMES）
#   - curl：healthcheck 用
#   - fonts-noto-cjk：Playwright 渲染中文頁面避免方塊字
#   - 其餘為 Chromium headless 執行所需的最小系統函式庫
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        tzdata \
        curl \
        ca-certificates \
        fonts-noto-cjk \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
        libatspi2.0-0 \
    && ln -fs /usr/share/zoneinfo/Asia/Taipei /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依賴先裝（利用 layer cache）
COPY requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/backend/requirements.txt

# Playwright Chromium 與其專屬系統相依由 playwright 官方腳本安裝，
# 上面 apt 區段已涵蓋大部分 lib，這裡只裝 browser 本體。
RUN python -m playwright install chromium

# 後端原始碼
COPY . /app/backend

# 預設建立 data 父目錄（不預先建立 funds 子目錄，以便首次執行 seed_demo_data 可透過單次原子 rename 建立 funds）
RUN mkdir -p /app/backend/data

EXPOSE 8000

# API 容器的 healthcheck（其他兩個 scheduler service 在 compose 端關閉）
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# 預設啟動 API；scheduler / twse 服務在 compose 端用 command 覆蓋
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
