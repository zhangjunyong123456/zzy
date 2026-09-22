<template>
  <div class="landing">
    <!-- 滚动色场：奶油 → 蜜桃 → 鼠尾草 → 暮杏 -->
    <div class="bg-field" :style="{ background: bgColor }"></div>
    <BlobCanvas />
    <div class="grain"></div>

    <nav class="nav">
      <router-link to="/" class="brand">UniGrow<span class="brand-dot">.</span></router-link>
      <div class="nav-right">
        <router-link to="/docs" class="nav-link">知识库</router-link>
        <router-link to="/chat" class="nav-cta" v-prox="{ pull: 4, radius: 100 }" @click="ripple">开始对话 →</router-link>
      </div>
    </nav>

    <!-- 01 HERO -->
    <section class="hero" ref="heroEl">
      <p class="hero-kicker reveal">智学成长 AGENT</p>
      <h1 class="hero-title reveal">UniGrow<span class="dot">.</span></h1>
      <p class="hero-sub reveal">一颗会成长的 AI，陪你走完大学的每一段路。</p>
      <p class="hero-line reveal">学习 · 科研 · 竞赛 · 求职 · 校园 —— 五种成长，一个入口。</p>
      <router-link to="/chat" class="hero-btn" v-prox="{ pull: 7, radius: 130 }" @click="ripple">与主 Agent 聊聊 →</router-link>
      <div class="scroll-cue" aria-hidden="true"><span></span></div>
    </section>

    <!-- 02 五大场景索引 -->
    <section class="scenes" ref="scenesEl">
      <header class="sec-head">
        <p class="sec-no reveal">02 — 场景</p>
        <h2 class="sec-title reveal">五颗成长星球</h2>
      </header>

      <div v-for="(s, i) in scenes" :key="s.name" class="scene-row reveal">
        <span class="scene-idx">0{{ i + 1 }}</span>
        <div class="scene-txt">
          <h3>{{ s.name }}</h3>
          <p>{{ s.desc }}</p>
        </div>
        <div class="orb" v-prox="{ pull: 0, radius: 150 }" :style="{ background: s.orb }"></div>
      </div>
    </section>

    <!-- 03 协同机制 -->
    <section class="flow" ref="flowEl">
      <header class="sec-head">
        <p class="sec-no reveal">03 — 协同</p>
        <h2 class="sec-title reveal">一句话，三个 Agent 同时出发</h2>
      </header>

      <div class="flow-steps">
        <div class="flow-line" aria-hidden="true"></div>
        <div v-for="f in flow" :key="f.t" class="flow-step reveal">
          <span class="flow-tag" :style="{ background: f.color }">{{ f.t }}</span>
          <h3>{{ f.h }}</h3>
          <p>{{ f.p }}</p>
        </div>
      </div>
    </section>

    <!-- 04 终章 -->
    <section class="finale" ref="finaleEl">
      <h2 class="finale-title reveal">让 AI<br />见证你的成长</h2>
      <div class="finale-actions reveal">
        <router-link to="/chat" class="big-btn" v-prox="{ pull: 7, radius: 130 }" @click="ripple">开始对话 →</router-link>
        <router-link to="/docs" class="ghost-btn" v-prox="{ pull: 4, radius: 110 }" @click="ripple">先看看知识库</router-link>
      </div>
    </section>

    <!-- 页脚：单行精简版 -->
    <footer class="site-footer">
      <div class="foot-inner reveal">
        <router-link to="/" class="f-logo">UniGrow<span class="brand-dot">.</span></router-link>
        <span class="f-desc">面向大学生全生命周期的多智能体成长平台 · 学生示例项目，仅用于学习演示 · Powered by DeepSeek API</span>
        <nav class="foot-links">
          <router-link to="/chat">开始对话</router-link>
          <router-link to="/docs">知识库</router-link>
          <router-link to="/profile">个人中心</router-link>
          <a href="https://platform.deepseek.com" target="_blank" rel="noopener">获取 API Key</a>
          <a href="https://www.ican-contest.org/" target="_blank" rel="noopener">iCAN 大赛</a>
        </nav>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import BlobCanvas from '../components/landing/BlobCanvas.vue'

/* ---- 按钮点击涟漪 ---- */
function ripple(e) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  const size = Math.max(r.width, r.height)
  const span = document.createElement('span')
  span.className = 'ripple'
  span.style.width = span.style.height = size + 'px'
  span.style.left = e.clientX - r.left - size / 2 + 'px'
  span.style.top = e.clientY - r.top - size / 2 + 'px'
  el.appendChild(span)
  setTimeout(() => span.remove(), 650)
}

const scenes = [
  { name: '学习 Agent', desc: '课件 PDF 即传即问，重点 · 难点 · 考点一键成笔记。', orb: 'radial-gradient(circle at 32% 28%, #ffd9c0, #ff9e7a 68%, #f08a63)' },
  { name: '科研 Agent', desc: '论文结构化解读，创新点与方法一目了然。', orb: 'radial-gradient(circle at 32% 28%, #dfe8cd, #a9bf92 68%, #8ba274)' },
  { name: '竞赛 Agent', desc: '赛题分析、技术路线、周计划与团队分工。', orb: 'radial-gradient(circle at 32% 28%, #ffe4c4, #f2b56b 68%, #dd9a4e)' },
  { name: '求职 Agent', desc: '简历逐句打磨，面试模拟到入职准备。', orb: 'radial-gradient(circle at 32% 28%, #cfe3c2, #9cc186 68%, #7ea768)' },
  { name: '校园 Agent', desc: '图书馆、教务、活动 —— 校园生活问它就好。', orb: 'radial-gradient(circle at 32% 28%, #cde6dd, #93c2ad 68%, #74a892)' }
]

const flow = [
  { t: '路由', color: '#f2b56b', h: '主 Agent 听懂你', p: '一句"我要参加 iCAN 比赛"，被拆解成三份子任务。' },
  { t: '并行', color: '#e8896b', h: '专业 Agent 同频出发', p: '竞赛、科研、学习三条链路同时生成，互不等待。' },
  { t: '汇总', color: '#93ab84', h: '一份成长行动建议', p: '跨 Agent 结论彼此衔接，落成可执行的下一步清单。' }
]

/* ---- 滚动驱动：背景色场插值 ---- */
const PALETTE = ['#fff6ea', '#fdece1', '#f2f0e4', '#f7e8d8']
const bgColor = ref(PALETTE[0])
let cur = [255, 246, 234], target = [255, 246, 234], rafBg, sections = []

const hex2rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))

const updateTarget = () => {
  const mid = window.scrollY + window.innerHeight * 0.5
  for (let i = 0; i < sections.length; i++) {
    const el = sections[i]
    if (!el) continue
    const top = el.offsetTop, bottom = top + el.offsetHeight
    if (mid >= top && mid < bottom) { target = hex2rgb(PALETTE[i]); break }
    if (mid >= bottom && i === sections.length - 1) target = hex2rgb(PALETTE[i])
  }
}
const loopBg = () => {
  cur = cur.map((c, i) => c + (target[i] - c) * 0.06)
  bgColor.value = `rgb(${cur.map((c) => Math.round(c)).join(',')})`
  rafBg = requestAnimationFrame(loopBg)
}

/* ---- 章节浮现 ---- */
let io
onMounted(() => {
  sections = [document.querySelector('.hero'), document.querySelector('.scenes'),
              document.querySelector('.flow'), document.querySelector('.finale')].filter(Boolean)
  window.addEventListener('scroll', updateTarget, { passive: true })
  updateTarget()
  loopBg()

  io = new IntersectionObserver(
    (es) => es.forEach((e) => e.isIntersecting && e.target.classList.add('in')),
    { threshold: 0.18 }
  )
  document.querySelectorAll('.reveal').forEach((el, i) => {
    el.style.transitionDelay = `${(i % 4) * 90}ms`
    io.observe(el)
  })
})
onBeforeUnmount(() => {
  cancelAnimationFrame(rafBg)
  io && io.disconnect()
  window.removeEventListener('scroll', updateTarget)
})
</script>

<style scoped>
.landing { position: relative; overflow-x: hidden; }

.bg-field { position: fixed; inset: 0; z-index: 0; transition: none; }
.grain {
  position: fixed; inset: -50%; z-index: 2; pointer-events: none; opacity: 0.055;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* ---- 导航 ---- */
.nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 10;
  display: flex; justify-content: space-between; align-items: center;
  padding: 22px clamp(20px, 4vw, 56px);
}
.brand {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: 24px; font-weight: 700; color: #3a2e24; text-decoration: none;
  letter-spacing: -0.5px;
}
.brand-dot { color: #e8896b; }
.nav-right { display: flex; align-items: center; gap: 26px; }
.nav-link {
  color: #6b5d50; text-decoration: none; font-size: 14px;
}
.nav-link:hover { color: #3a2e24; }
.nav-cta {
  color: #3a2e24; text-decoration: none; font-size: 14px; font-weight: 600;
  padding: 10px 20px; border-radius: 999px;
  border: 1.5px solid rgba(58, 46, 36, 0.25);
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 1px * var(--prox, 0)), 0);
  transition: background 0.3s, color 0.3s, transform 0.3s;
}
.nav-cta:hover { background: #3a2e24; color: #fff6ea; transform: translateY(-1px); }

/* ---- 通用浮现 ---- */
.reveal { opacity: 0; translate: 0 26px; transition: opacity 0.9s ease, translate 0.9s cubic-bezier(0.16, 1, 0.3, 1); }
.reveal.in { opacity: 1; translate: none; }

section { position: relative; z-index: 3; }

/* ---- Hero：海报式满屏 ---- */
.hero {
  min-height: 100svh;
  display: flex; flex-direction: column; justify-content: center;
  align-items: center; text-align: center;
  padding: 0 24px;
}
/* 柔和底衬：把 hero 文字从彩色 blob 上托起来，保证可读性 */
.hero::before {
  content: '';
  position: absolute; inset: -8% -12%;
  z-index: -1;
  background: radial-gradient(ellipse 62% 55% at 50% 46%, rgba(255, 246, 234, 0.88) 0%, rgba(255, 246, 234, 0.55) 52%, transparent 78%);
  pointer-events: none;
}
.hero-kicker {
  font-size: 13px; letter-spacing: 0.5em; color: #b08a6e; margin: 0 0 18px;
}
.hero-title {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: clamp(84px, 17vw, 230px);
  line-height: 0.95; letter-spacing: -0.03em;
  color: #3a2e24; margin: 0;
  font-weight: 700;
}
.hero-title .dot { color: #e8896b; }
.hero-sub {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: clamp(19px, 2.6vw, 30px); color: #4a3c30;
  margin: 30px 0 8px;
}
.hero-line { font-size: 14px; color: #8a7a6a; margin: 0 0 36px; letter-spacing: 0.08em; }
.hero-btn {
  font-size: 16px; font-weight: 600; text-decoration: none;
  color: #fff6ea; background: #3a2e24;
  padding: 16px 34px; border-radius: 999px;
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 3px * var(--prox, 0)), 0);
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), background 0.35s, box-shadow 0.35s;
  box-shadow: 0 10px 30px rgba(58, 46, 36, 0.18);
}
.hero-btn:hover {
  transform: translateY(-3px); background: #e8896b;
  box-shadow: 0 16px 40px rgba(232, 137, 107, 0.35);
}
.scroll-cue { position: absolute; bottom: 34px; left: 50%; width: 1px; height: 52px; overflow: hidden; }
.scroll-cue span {
  display: block; width: 1px; height: 100%;
  background: linear-gradient(#b08a6e, transparent);
  animation: cue 2.2s ease-in-out infinite;
}
@keyframes cue { 0% { transform: translateY(-100%); } 60% { transform: translateY(0); } 100% { transform: translateY(100%); } }

/* ---- 场景索引：杂志式行 ---- */
.scenes { padding: 16vh clamp(20px, 6vw, 90px); max-width: 1200px; margin: 0 auto; }
.sec-head { margin-bottom: 7vh; }
.sec-no { font-size: 12px; letter-spacing: 0.4em; color: #b08a6e; margin: 0 0 12px; }
.sec-title {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: clamp(34px, 5vw, 62px); color: #3a2e24; margin: 0; font-weight: 700;
}
.scene-row {
  display: grid; grid-template-columns: 70px 1fr auto;
  align-items: center; gap: clamp(16px, 3vw, 40px);
  padding: 4.2vh 0;
  border-bottom: 1px solid rgba(58, 46, 36, 0.12);
}
.scene-row:last-child { border-bottom: none; }
.scene-idx {
  font-family: Georgia, serif; font-style: italic;
  font-size: clamp(18px, 2vw, 26px); color: #e8896b;
}
.scene-txt h3 {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: clamp(26px, 3.6vw, 46px); color: #3a2e24; margin: 0 0 6px; font-weight: 700;
  transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}
.scene-txt p { font-size: 15px; color: #8a7a6a; margin: 0; }
.orb {
  width: clamp(56px, 6vw, 88px); aspect-ratio: 1; border-radius: 50%;
  box-shadow: inset -10px -14px 24px rgba(120, 80, 50, 0.18), 0 18px 34px rgba(160, 110, 80, 0.22);
  /* 接近感应：光标靠近时星球抬起、放大并发光 */
  transform: translate3d(0, calc(-10px * var(--prox, 0)), 0) scale(calc(1 + 0.1 * var(--prox, 0)));
  filter: brightness(calc(1 + 0.1 * var(--prox, 0))) saturate(calc(1 + 0.18 * var(--prox, 0)))
          drop-shadow(0 0 calc(22px * var(--prox, 0)) rgba(255, 158, 122, 0.4));
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1), filter 0.5s;
}
.scene-row:hover .orb { transform: translateY(-10px) scale(1.06); }
.scene-row:hover h3 { transform: translateX(10px); }

/* ---- 协同 ---- */
.flow { padding: 14vh clamp(20px, 6vw, 90px); max-width: 860px; margin: 0 auto; }
.flow-steps { position: relative; padding-left: clamp(28px, 4vw, 56px); }
.flow-line {
  position: absolute; left: 8px; top: 8px; bottom: 8px; width: 2px;
  background: linear-gradient(#f2b56b, #e8896b, #93ab84); opacity: 0.5;
}
.flow-step { padding: 4.5vh 0; }
.flow-tag {
  display: inline-block; font-size: 12px; letter-spacing: 0.3em;
  color: #3a2e24; padding: 6px 14px; border-radius: 999px; margin-bottom: 14px;
}
.flow-step h3 {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: clamp(24px, 3.2vw, 40px); color: #3a2e24; margin: 0 0 8px; font-weight: 700;
}
.flow-step p { font-size: 15px; color: #8a7a6a; margin: 0; max-width: 560px; }

/* ---- 终章 ---- */
.finale {
  min-height: 92svh;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
  text-align: center; padding: 10vh 24px 0;
}
.finale-title {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: clamp(40px, 7vw, 96px); color: #3a2e24; margin: 0 0 5vh; font-weight: 700; line-height: 1.15;
}
.finale-actions { display: flex; gap: 18px; flex-wrap: wrap; justify-content: center; }
.big-btn {
  font-size: 17px; font-weight: 600; text-decoration: none;
  color: #fff6ea; background: #3a2e24;
  padding: 18px 44px; border-radius: 999px;
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 3px * var(--prox, 0)), 0);
  box-shadow: 0 12px 34px rgba(58, 46, 36, 0.2);
  transition: transform 0.35s, background 0.35s;
}
.big-btn:hover { transform: translateY(-3px); background: #e8896b; }
.ghost-btn {
  font-size: 15px; text-decoration: none; color: #6b5d50;
  padding: 18px 30px; border-radius: 999px; border: 1.5px solid rgba(58, 46, 36, 0.22);
  transform: translate3d(var(--px, 0px), calc(var(--py, 0px) - 2px * var(--prox, 0)), 0);
  transition: transform 0.3s, color 0.3s, border-color 0.3s;
}
.ghost-btn:hover { color: #3a2e24; border-color: #3a2e24; }

/* ---- 页脚（单行精简：品牌 + 一句话 + 关键链接） ---- */
.site-footer {
  position: relative; z-index: 3;
  padding: 8vh clamp(20px, 6vw, 90px) 5vh;
}
.foot-inner {
  max-width: 1200px; margin: 0 auto;
  border-top: 1px solid rgba(58, 46, 36, 0.12);
  padding-top: 26px;
  display: flex; align-items: center; flex-wrap: wrap;
  gap: 14px 26px;
}
.f-logo {
  font-family: Georgia, 'Songti SC', 'SimSun', serif;
  font-size: 22px; font-weight: 700; color: #3a2e24;
  text-decoration: none; letter-spacing: -0.5px;
  flex-shrink: 0;
}
.f-desc { font-size: 12.5px; color: #a89a8a; flex: 1; min-width: 260px; }
.foot-links { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.foot-links a { font-size: 13.5px; color: #6b5d50; text-decoration: none; transition: color 0.25s; }
.foot-links a:hover { color: #e8896b; }

@media (max-width: 640px) {
  .scene-row { grid-template-columns: 40px 1fr auto; }
  .nav { padding: 16px 20px; }
}
@media (prefers-reduced-motion: reduce) {
  .reveal { transition: none; opacity: 1; translate: none; }
  .scroll-cue span { animation: none; }
}
</style>
