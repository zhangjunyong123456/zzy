/**
 * 全局接近感应（proximity）系统
 *
 * 光标靠近注册元素时，为其写入三个 CSS 变量，由各组件样式自行消费：
 *   --prox  0~1 接近度（按光标到元素边缘的距离计算，碰到边缘即 1）
 *   --px    磁吸横向偏移（px 值，元素朝光标方向轻微倾斜，pull=0 时不写入）
 *   --py    磁吸纵向偏移（px 值）
 *
 * 通过 v-prox 指令使用：v-prox 或 v-prox="{ pull: 6, radius: 120 }"
 * 触屏 / prefers-reduced-motion 下自动禁用（不注册、不写变量）。
 */

const items = new Set() // { el, pull, radius }
let px = -9999
let py = -9999
let raf = 0
let bound = false

function fine() {
  return (
    window.matchMedia('(pointer: fine)').matches &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

function schedule() {
  // 后台标签页 rAF 被浏览器冻结，退化为同步测量（也保证合成事件可测）
  if (document.hidden) {
    measure()
    return
  }
  if (!raf && items.size) raf = requestAnimationFrame(measure)
}

function measure() {
  raf = 0
  for (const it of items) {
    const el = it.el
    const r = el.getBoundingClientRect()
    if (!r.width || !r.height) continue
    const cx = r.left + r.width / 2
    const cy = r.top + r.height / 2
    // 光标到元素边缘的距离（元素内部视为 0）
    const dx = Math.max(Math.abs(px - cx) - r.width / 2, 0)
    const dy = Math.max(Math.abs(py - cy) - r.height / 2, 0)
    const d = Math.hypot(dx, dy)
    const prox = Math.max(0, Math.min(1, 1 - d / it.radius))

    if (prox > 0) {
      const s = el.style
      s.setProperty('--prox', prox.toFixed(3))
      if (it.pull > 0) {
        // 元素朝光标方向偏移 pull*prox，光标越近吸得越多
        const vx = px - cx
        const vy = py - cy
        const dist = Math.hypot(vx, vy) || 1
        const k = Math.min(it.pull * prox, dist)
        s.setProperty('--px', ((vx / dist) * k).toFixed(1) + 'px')
        s.setProperty('--py', ((vy / dist) * k).toFixed(1) + 'px')
      }
      el.__proxOn = true
    } else if (el.__proxOn) {
      // 只在刚离开时归零一次，避免逐帧无效写入
      const s = el.style
      s.setProperty('--prox', '0')
      s.setProperty('--px', '0px')
      s.setProperty('--py', '0px')
      el.__proxOn = false
    }
  }
}

function onMove(e) {
  px = e.clientX
  py = e.clientY
  schedule()
}

function bind() {
  if (bound || !fine()) return
  bound = true
  window.addEventListener('pointermove', onMove, { passive: true })
  // 滚动时元素位置变化，重新测量
  window.addEventListener('scroll', schedule, { passive: true })
}

export function registerProx(el, opts = {}) {
  if (!fine()) return
  bind()
  items.add({
    el,
    pull: Math.max(0, opts.pull ?? 6),
    radius: Math.max(40, opts.radius ?? 120)
  })
  schedule()
}

export function unregisterProx(el) {
  for (const it of items) {
    if (it.el === el) items.delete(it)
  }
}
