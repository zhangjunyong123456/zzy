<template>
  <!-- 跟随光环：光点紧跟 + 圆环缓动追随（悬停可点元素放大，按下收缩） -->
  <div
    ref="ringEl"
    class="fx-ring"
    :class="{ show: cursorShown, active: ringActive, press: ringPress }"
    aria-hidden="true"
  ><i></i></div>
  <div ref="dotEl" class="fx-dot" :class="{ show: cursorShown }" aria-hidden="true"></div>
  <canvas ref="cv" class="fx-canvas" aria-hidden="true"></canvas>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'

/* 全局鼠标特效：
   1) 跟随光环（光点 + 缓动圆环，悬停可点元素时放大）
   2) 滑动粒子拖尾
   3) 点击迸发（扩散圆环 + 星星/爱心）
   全部 pointer-events:none，不影响任何交互 */

const cv = ref(null)
const dotEl = ref(null)
const ringEl = ref(null)
const cursorShown = ref(false)
const ringActive = ref(false)
const ringPress = ref(false)

let ctx = null
let raf = 0
let parts = []
let dpr = 1
let lastX = -1
let lastY = -1

// 光环跟随状态：tx/ty 目标，cx/cy 光点，rx/ry 圆环（更慢，产生拖拽感）
let tx = -100
let ty = -100
let cx = -100
let cy = -100
let rx = -100
let ry = -100
let pressTimer = 0

// 与站点装饰色一致：珊瑚/焦糖/鼠尾草/青玉/蜜桃
const PALETTE = ['#e8896b', '#dfa453', '#93ab84', '#7fb39c', '#f2a58d', '#f7c59f']
const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches
// 悬停这些元素时光环放大提示「可点」
const INTERACTIVE = 'a, button, input, textarea, select, label, [role="button"], .scene-card, .pet'

function resize() {
  if (!cv.value) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  cv.value.width = Math.floor(window.innerWidth * dpr)
  cv.value.height = Math.floor(window.innerHeight * dpr)
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function pick(arr) {
  return arr[(Math.random() * arr.length) | 0]
}

function push(p) {
  if (parts.length > 260) parts.shift()
  parts.push(p)
}

/* 拖尾粒子：微微上飘、渐隐缩小 */
function spawnTrail(x, y) {
  push({
    x: x + (Math.random() - 0.5) * 8,
    y: y + (Math.random() - 0.5) * 8,
    vx: (Math.random() - 0.5) * 0.5,
    vy: (Math.random() - 0.5) * 0.5 - 0.25,
    g: -0.012,
    life: 1,
    decay: 0.02 + Math.random() * 0.018,
    size: 1.8 + Math.random() * 2.6,
    color: pick(PALETTE),
    shape: Math.random() < 0.12 ? 'star' : 'dot'
  })
}

/* 点击迸发：一圈圆环 + 四散的圆点/星星/爱心 */
function burst(x, y) {
  push({ ring: true, x, y, r: 6, vr: 3.2, life: 1, decay: 0.05, color: '#e8896b' })
  const n = 12 + ((Math.random() * 4) | 0)
  for (let i = 0; i < n; i++) {
    const a = (Math.PI * 2 * i) / n + Math.random() * 0.6
    const sp = 1.8 + Math.random() * 2.6
    const r = Math.random()
    push({
      x,
      y,
      vx: Math.cos(a) * sp,
      vy: Math.sin(a) * sp - 0.6,
      g: 0.05,
      life: 1,
      decay: 0.02 + Math.random() * 0.018,
      size: 2 + Math.random() * 2.4,
      color: pick(PALETTE),
      shape: r < 0.16 ? 'heart' : r < 0.4 ? 'star' : 'dot'
    })
  }
}

function drawParts() {
  for (const p of parts) {
    const a = Math.max(0, Math.min(1, p.life))
    ctx.globalAlpha = a
    if (p.ring) {
      ctx.strokeStyle = p.color
      ctx.lineWidth = 2.4 * a
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.stroke()
      continue
    }
    if (p.shape === 'dot') {
      ctx.fillStyle = p.color
      ctx.beginPath()
      ctx.arc(p.x, p.y, Math.max(0.4, p.size * a), 0, Math.PI * 2)
      ctx.fill()
    } else {
      ctx.fillStyle = p.shape === 'heart' ? '#e8896b' : p.color
      ctx.font = `${(p.size * 3) | 0}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(p.shape === 'heart' ? pick(['💗', '✨']) : '✦', p.x, p.y)
    }
  }
  ctx.globalAlpha = 1
}

function tick() {
  ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
  parts = parts.filter((p) => p.life > 0)
  for (const p of parts) {
    p.life -= p.decay
    if (p.ring) {
      p.r += p.vr * p.life
      continue
    }
    p.vx *= 0.96
    p.vy = p.vy * 0.96 + p.g
    p.x += p.vx
    p.y += p.vy
  }
  drawParts()

  // 光环缓动跟随：光点快、圆环慢
  if (cursorShown.value) {
    cx += (tx - cx) * 0.55
    cy += (ty - cy) * 0.55
    rx += (tx - rx) * 0.16
    ry += (ty - ry) * 0.16
    if (dotEl.value) dotEl.value.style.transform = `translate3d(${cx}px, ${cy}px, 0)`
    if (ringEl.value) ringEl.value.style.transform = `translate3d(${rx}px, ${ry}px, 0)`
  }
  raf = requestAnimationFrame(tick)
}

function onMove(e) {
  if (e.pointerType === 'touch') {
    cursorShown.value = false
    return
  }
  if (REDUCED) return

  // 光环目标点 + 悬停态检测
  tx = e.clientX
  ty = e.clientY
  if (!cursorShown.value) {
    cx = rx = tx
    cy = ry = ty
    cursorShown.value = true
  }
  ringActive.value = !!(e.target instanceof Element && e.target.closest(INTERACTIVE))

  // 拖尾粒子
  if (lastX < 0) {
    lastX = e.clientX
    lastY = e.clientY
    return
  }
  const dist = Math.hypot(e.clientX - lastX, e.clientY - lastY)
  if (dist < 12) return
  const midX = (e.clientX + lastX) / 2
  const midY = (e.clientY + lastY) / 2
  lastX = e.clientX
  lastY = e.clientY
  spawnTrail(e.clientX, e.clientY)
  if (dist > 48) spawnTrail(midX, midY) // 快速划动补一颗粒子，拖尾更连贯
}

function onDown(e) {
  if (REDUCED) return
  ringPress.value = true
  clearTimeout(pressTimer)
  pressTimer = setTimeout(() => (ringPress.value = false), 220)
  burst(e.clientX, e.clientY)
}

function onLeave() {
  cursorShown.value = false
}

onMounted(() => {
  ctx = cv.value.getContext('2d')
  resize()
  window.addEventListener('resize', resize)
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerdown', onDown)
  window.addEventListener('blur', onLeave)
  document.documentElement.addEventListener('mouseleave', onLeave)
  raf = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', resize)
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerdown', onDown)
  window.removeEventListener('blur', onLeave)
  document.documentElement.removeEventListener('mouseleave', onLeave)
  clearTimeout(pressTimer)
})
</script>

<style scoped>
/* 跟随光点（紧跟鼠标） */
.fx-dot {
  position: fixed;
  left: -3px;
  top: -3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #e8896b;
  box-shadow: 0 0 8px rgba(232, 137, 107, 0.8);
  opacity: 0;
  transition: opacity 0.25s;
  will-change: transform;
  pointer-events: none;
  z-index: 3101;
}
.fx-dot.show { opacity: 0.9; }

/* 缓动跟随圆环 */
.fx-ring {
  position: fixed;
  left: -17px;
  top: -17px;
  width: 34px;
  height: 34px;
  opacity: 0;
  transition: opacity 0.25s;
  will-change: transform;
  pointer-events: none;
  z-index: 3100;
}
.fx-ring.show { opacity: 1; }
.fx-ring i {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 1.5px solid rgba(232, 137, 107, 0.5);
  box-shadow: 0 0 14px rgba(232, 137, 107, 0.25), inset 0 0 8px rgba(232, 137, 107, 0.12);
  transition:
    transform 0.25s cubic-bezier(0.16, 1, 0.3, 1),
    border-color 0.25s,
    box-shadow 0.25s;
  position: relative;
}
/* 旋转的高光弧，让圆环有生命感 */
.fx-ring i::after {
  content: '';
  position: absolute;
  inset: -1.5px;
  border-radius: 50%;
  border: 1.5px solid transparent;
  border-top-color: rgba(223, 164, 83, 0.9);
  animation: fx-spin 2.6s linear infinite;
}
@keyframes fx-spin {
  to { transform: rotate(360deg); }
}
/* 悬停可点元素：放大提亮 */
.fx-ring.active i {
  transform: scale(1.55);
  border-color: rgba(232, 137, 107, 0.85);
  box-shadow: 0 0 18px rgba(232, 137, 107, 0.4), inset 0 0 10px rgba(232, 137, 107, 0.18);
}
/* 按下：收缩脉冲 */
.fx-ring.press i { transform: scale(0.8); }

.fx-canvas {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 3000;
}
</style>
