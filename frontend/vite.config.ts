import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, URL as NodeURL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import type { Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const DEFAULT_SITE_URL = 'http://127.0.0.1:5173'
const DEFAULT_API_TARGET = 'http://127.0.0.1:8000'
const SITE_URL_VALIDATION_ERROR =
  'Invalid VITE_SITE_URL: must be an http/https origin without credentials, path, query, or hash.'

export function normalizeSiteUrl(raw?: string): string {
  const trimmed = raw?.trim() || DEFAULT_SITE_URL
  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  if (parsed.username !== '' || parsed.password !== '') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  if (parsed.search !== '' || parsed.hash !== '') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  if (parsed.pathname !== '/') {
    throw new Error(SITE_URL_VALIDATION_ERROR)
  }
  return parsed.origin
}

function buildRobotsTxt(siteUrl: string): string {
  return `User-agent: *\nAllow: /\n\nSitemap: ${siteUrl}/sitemap.xml\n`
}

function buildSitemapXml(siteUrl: string): string {
  const entries = [
    { path: '/', changefreq: 'daily', priority: '1.0' },
    { path: '/slot', changefreq: 'daily', priority: '0.9' },
    { path: '/holdings', changefreq: 'daily', priority: '0.8' },
    { path: '/weights', changefreq: 'daily', priority: '0.8' },
    { path: '/about', changefreq: 'monthly', priority: '0.6' },
    { path: '/faq', changefreq: 'monthly', priority: '0.6' },
  ]
  const urls = entries
    .map(
      (e) =>
        `  <url>\n    <loc>${siteUrl}${e.path}</loc>\n    <changefreq>${e.changefreq}</changefreq>\n    <priority>${e.priority}</priority>\n  </url>`,
    )
    .join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`
}

/**
 * 1) 將 index.html 內的 __SITE_URL__ 以驗證過之 VITE_SITE_URL origin（或預設 http://127.0.0.1:5173）取代，
 *    確保不會殘留未解析的 placeholder 或注入非法字元。
 * 2) 停用 Vite 預設整個 public/ 原樣複製，改於 Rollup `generateBundle` 階段透過 `this.emitFile`
 *    輸出白名單資產（`favicon.svg`、`robots.txt`、`sitemap.xml`），完全遵循 resolved `outDir`，
 *    且不會在 Vitest 單元測試或 dev server 關閉時誤寫檔案。
 */
function siteMetadataAndSafePublicPlugin(siteUrl: string): Plugin {
  const faviconSvgPath = resolve(__dirname, 'public', 'favicon.svg')

  return {
    name: 'destinyorder-site-metadata-and-safe-public',
    transformIndexHtml(html) {
      return html.replaceAll('__SITE_URL__', siteUrl)
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const cleanUrl = (req.url || '/').split('?')[0]
        if (cleanUrl === '/favicon.svg' && existsSync(faviconSvgPath)) {
          res.setHeader('Content-Type', 'image/svg+xml')
          res.end(readFileSync(faviconSvgPath))
          return
        }
        if (cleanUrl === '/robots.txt') {
          res.setHeader('Content-Type', 'text/plain; charset=utf-8')
          res.end(buildRobotsTxt(siteUrl))
          return
        }
        if (cleanUrl === '/sitemap.xml') {
          res.setHeader('Content-Type', 'application/xml; charset=utf-8')
          res.end(buildSitemapXml(siteUrl))
          return
        }
        next()
      })
    },
    generateBundle() {
      if (existsSync(faviconSvgPath)) {
        this.emitFile({
          type: 'asset',
          fileName: 'favicon.svg',
          source: readFileSync(faviconSvgPath),
        })
      }
      this.emitFile({
        type: 'asset',
        fileName: 'robots.txt',
        source: buildRobotsTxt(siteUrl),
      })
      this.emitFile({
        type: 'asset',
        fileName: 'sitemap.xml',
        source: buildSitemapXml(siteUrl),
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const siteUrl = normalizeSiteUrl(process.env.VITE_SITE_URL || env.VITE_SITE_URL)
  const apiProxyTarget = (
    process.env.BACKEND_API_TARGET ||
    env.BACKEND_API_TARGET ||
    DEFAULT_API_TARGET
  ).trim()

  return {
    publicDir: false,
    define: {
      'import.meta.env.VITE_SITE_URL': JSON.stringify(siteUrl),
    },
    plugins: [vue(), vueJsx(), siteMetadataAndSafePublicPlugin(siteUrl)],
    resolve: {
      alias: {
        '@': fileURLToPath(new NodeURL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        // 開發階段把 /api/* 轉發到 FastAPI 後端（預設 http://127.0.0.1:8000，可由 server-only BACKEND_API_TARGET 覆寫）。
        '/api': {
          target: apiProxyTarget,
          changeOrigin: false,
        },
      },
    },
  }
})
