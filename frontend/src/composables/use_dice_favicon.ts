import { onMounted, onUnmounted } from 'vue'

const SIZE = 64
const FRAME_MS = 320

/**
 * 在分頁列上常駐播放「擲骰子」動畫的 favicon。
 *
 * 透過 `<canvas>` 每幀重繪一顆隨機點數骰子，把 dataURL 灌進
 * `<link rel="icon">.href`。背景分頁時瀏覽器會自動 throttle setInterval，
 * 不必額外處理省電邏輯。
 */
export function use_dice_favicon(): void {
  let canvas: HTMLCanvasElement | null = null
  let link: HTMLLinkElement | null = null
  let timer: number | null = null
  let face = 6

  function _next_face(): number {
    let nf = face
    while (nf === face) nf = 1 + Math.floor(Math.random() * 6)
    face = nf
    return face
  }

  function _tick(): void {
    if (!canvas || !link) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    _draw_face(ctx, _next_face())
    link.href = canvas.toDataURL('image/png')
  }

  onMounted(() => {
    if (typeof document === 'undefined') return
    // Prerender 環境（Puppeteer）跳過：避免把 base64 dataURL 灌進 HTML，
    // 害 Google Search 抓不到實體 favicon 檔（dataURI favicon 不會被收錄）。
    if ((window as unknown as { __PRERENDER__?: boolean }).__PRERENDER__) {
      return
    }
    canvas = document.createElement('canvas')
    canvas.width = SIZE
    canvas.height = SIZE

    // 新建獨立的動態 <link>，不去動原本 index.html 的多尺寸 icon 宣告，
    // 確保爬蟲與 SEO 工具仍能讀到 favicon.ico / 多尺寸 PNG。
    link = document.createElement('link')
    link.rel = 'icon'
    link.type = 'image/png'
    link.setAttribute('data-dice-favicon', '')
    document.head.appendChild(link)

    _tick()
    timer = window.setInterval(_tick, FRAME_MS)
  })

  onUnmounted(() => {
    if (timer !== null) window.clearInterval(timer)
    if (link && link.parentNode) link.parentNode.removeChild(link)
  })
}

function _draw_face(ctx: CanvasRenderingContext2D, face: number): void {
  ctx.clearRect(0, 0, SIZE, SIZE)

  // 骰子本體：紫→藍漸層
  const body = ctx.createLinearGradient(0, 0, SIZE, SIZE)
  body.addColorStop(0, '#7c5cff')
  body.addColorStop(1, '#3a8dff')
  ctx.fillStyle = body
  _round_rect(ctx, 6, 6, SIZE - 12, SIZE - 12, 12)
  ctx.fill()

  // 上層高光（玻璃感）
  const hl = ctx.createLinearGradient(0, 0, 0, SIZE)
  hl.addColorStop(0, 'rgba(255,255,255,0.32)')
  hl.addColorStop(0.6, 'rgba(255,255,255,0)')
  ctx.fillStyle = hl
  _round_rect(ctx, 6, 6, SIZE - 12, SIZE - 12, 12)
  ctx.fill()

  // 邊框
  ctx.strokeStyle = 'rgba(26,31,58,0.3)'
  ctx.lineWidth = 2
  _round_rect(ctx, 6, 6, SIZE - 12, SIZE - 12, 12)
  ctx.stroke()

  // 點數
  ctx.fillStyle = '#ffffff'
  for (const [cx, cy] of _pip_positions(face)) {
    ctx.beginPath()
    ctx.arc(cx, cy, 4.2, 0, Math.PI * 2)
    ctx.fill()
  }
}

function _round_rect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function _pip_positions(face: number): Array<[number, number]> {
  const L = 20
  const M = 32
  const R = 44
  const T = 18
  const MD = 32
  const B = 46
  switch (face) {
    case 1:
      return [[M, MD]]
    case 2:
      return [
        [L, T],
        [R, B],
      ]
    case 3:
      return [
        [L, T],
        [M, MD],
        [R, B],
      ]
    case 4:
      return [
        [L, T],
        [R, T],
        [L, B],
        [R, B],
      ]
    case 5:
      return [
        [L, T],
        [R, T],
        [M, MD],
        [L, B],
        [R, B],
      ]
    case 6:
      return [
        [L, T],
        [R, T],
        [L, MD],
        [R, MD],
        [L, B],
        [R, B],
      ]
    default:
      return [[M, MD]]
  }
}
