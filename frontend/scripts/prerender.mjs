/**
 * 靜態預渲染腳本：用 Puppeteer 走訪每條路由，把 Vue 掛載後的 HTML 寫回 dist。
 *
 * 為什麼這樣做：搜尋引擎爬蟲對 SPA 純 CSR 頁面有時只看得到空殼 <div id="app"></div>，
 * 預渲染後能直接讀到完整文字內容，提升收錄與首次載入可讀性。
 *
 * 流程：
 *   1) 用 node:http 啟一個靜態檔伺服器，根目錄指向 dist/
 *   2) Puppeteer 走訪 ROUTES 中每條路徑
 *   3) 等 Vue 掛載完畢（#app 內有子節點 + 主要 <main> 出現）
 *   4) 抓取 document.documentElement.outerHTML 寫回 dist/<route>/index.html
 */

import { createServer } from 'node:http'
import { promises as fs, existsSync, createReadStream, statSync } from 'node:fs'
import { extname, join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

import puppeteer from 'puppeteer'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const DIST_DIR = resolve(__dirname, '..', 'dist')

const ROUTES = ['/', '/slot', '/holdings', '/weights', '/about', '/faq']

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.m4a': 'audio/mp4',
  '.mp3': 'audio/mpeg',
}

function _start_static_server(root) {
  return new Promise((resolve_) => {
    const server = createServer((req, res) => {
      try {
        const url_path = decodeURIComponent((req.url || '/').split('?')[0])
        let fs_path = join(root, url_path)
        if (existsSync(fs_path) && statSync(fs_path).isDirectory()) {
          fs_path = join(fs_path, 'index.html')
        }
        if (!existsSync(fs_path)) {
          // SPA fallback
          fs_path = join(root, 'index.html')
        }
        const ext = extname(fs_path).toLowerCase()
        res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' })
        createReadStream(fs_path).pipe(res)
      } catch (err) {
        res.writeHead(500)
        res.end(String(err))
      }
    })
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      resolve_({ server, port })
    })
  })
}

async function _render_route(browser, base_url, route) {
  const page = await browser.newPage()
  await page.setViewport({ width: 1200, height: 800 })

  // 注入旗標讓前端在需要時可偵測 prerender 環境（如不放音訊／不打點）
  await page.evaluateOnNewDocument(() => {
    window.__PRERENDER__ = true
  })

  // 攔截對預渲染文字內容無影響的媒體與字型資源以加速建置
  await page.setRequestInterception(true)
  page.on('request', (req) => {
    const type = req.resourceType()
    if (type === 'media' || type === 'font') {
      return req.abort()
    }
    return req.continue()
  })

  const url = `${base_url}${route}`
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 30_000 })

  // 等 Vue 掛上去：#app 有子節點且 <main> 出現
  await page.waitForFunction(
    () => {
      const app = document.getElementById('app')
      if (!app || app.children.length === 0) return false
      return !!app.querySelector('main, article, section')
    },
    { timeout: 15_000 },
  )

  // 給 router.afterEach 跑完 + 動畫第一幀刷出來
  await new Promise((r) => setTimeout(r, 300))

  const html = await page.evaluate(() => {
    return '<!DOCTYPE html>\n' + document.documentElement.outerHTML
  })

  await page.close()
  if (html.includes(base_url)) {
    throw new Error(
      `[prerender] 路由 ${route} 輸出之 HTML 殘留暫存伺服器 origin (${base_url})，請確認 VITE_SITE_URL 注入設定。`,
    )
  }
  return html
}

async function _write_route_html(route, html) {
  const out_dir =
    route === '/' ? DIST_DIR : join(DIST_DIR, route.replace(/^\//, ''))
  await fs.mkdir(out_dir, { recursive: true })
  const out_file = join(out_dir, 'index.html')
  await fs.writeFile(out_file, html, 'utf8')
  return out_file
}

async function main() {
  if (!existsSync(DIST_DIR)) {
    console.error(`[prerender] dist 目錄不存在：${DIST_DIR}`)
    console.error('[prerender] 請先執行 vite build 再跑此腳本。')
    process.exit(1)
  }

  const { server, port } = await _start_static_server(DIST_DIR)
  const base_url = `http://127.0.0.1:${port}`
  console.log(`[prerender] 靜態伺服器啟動於 ${base_url}`)

  const launch_opts = {
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
    ],
  }
  // Docker 內若已有系統 chromium，可用 PUPPETEER_EXECUTABLE_PATH 指定
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    launch_opts.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH
  }

  const browser = await puppeteer.launch(launch_opts)

  try {
    for (const route of ROUTES) {
      const t0 = Date.now()
      const html = await _render_route(browser, base_url, route)
      const out = await _write_route_html(route, html)
      const kb = (Buffer.byteLength(html, 'utf8') / 1024).toFixed(1)
      console.log(
        `[prerender] ${route.padEnd(12)} → ${out}  (${kb} KB, ${Date.now() - t0}ms)`,
      )
    }
  } finally {
    await browser.close()
    server.close()
  }

  console.log('[prerender] 完成。')
}

main().catch((err) => {
  console.error('[prerender] 失敗：', err)
  process.exit(1)
})
