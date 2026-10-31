# syntax=docker/dockerfile:1.7

# ----- Stage 1: build -----
# 使用 Debian slim（非 Alpine）以便讓 Puppeteer 的 Chromium 二進位順利執行；
# Alpine 採用 musl libc，Puppeteer 內建 Chromium 需要 glibc。
# 對齊 Node 24 LTS（滿足 @tsconfig/node24 與 Vite 7 engines 要求）。
FROM node:24-bookworm-slim AS build-stage

ARG VITE_SITE_URL=http://127.0.0.1:5173
ENV NODE_ENV=production \
    CI=true \
    VITE_SITE_URL=${VITE_SITE_URL} \
    # 跳過 Puppeteer 在 npm install 時的 Chrome 下載，
    # 改用下方 apt 安裝的系統 Chromium，可大幅縮短 Docker build 時間
    PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# 安裝系統 Chromium 與最小化的字型 / 渲染依賴
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安裝依賴（含 devDependencies 才能跑 vite build / vue-tsc / puppeteer prerender）
COPY package*.json ./
RUN npm ci --include=dev

# 複製原始碼並產生 production bundle + prerender
COPY . .
RUN npm run build

# ----- Stage 2: nginx 靜態檔伺服 + /api 反向代理 -----
FROM nginx:alpine AS production-stage

# 套件安全性更新（不安裝任何額外套件）
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# 靜態檔（已包含 prerender 後的 about/faq/slot/holdings/weights index.html）
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 覆蓋預設 server block
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
