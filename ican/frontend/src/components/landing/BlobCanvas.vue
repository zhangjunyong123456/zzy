<template>
  <canvas ref="cv" class="blob-canvas" aria-hidden="true"></canvas>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as THREE from 'three'

const cv = ref(null)
let renderer, scene, camera, raf, cleanup

onMounted(() => {
  const canvas = cv.value
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100)
  camera.position.z = 7.5

  const NOISE = /* glsl */ `
  vec3 mod289(vec3 x){return x - floor(x*(1.0/289.0))*289.0;}
  vec4 mod289(vec4 x){return x - floor(x*(1.0/289.0))*289.0;}
  vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
  vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314*r;}
  float snoise(vec3 v){
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
        i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0*floor(p*ns.z*ns.z);
    vec4 x_ = floor(j*ns.z);
    vec4 y_ = floor(j - 7.0*x_);
    vec4 x = x_*ns.x + ns.yyyy;
    vec4 y = y_*ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m*m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
  }`

  const VERT = /* glsl */ `
  uniform float uTime; uniform float uAmp; uniform float uFreq;
  uniform vec3 uHit; uniform float uHover;
  varying vec3 vNormal; varying float vNoise;
  ${NOISE}
  void main(){
    // 液态流动：噪声域沿不同方向随时间漂移，表面持续对流
    float n1 = snoise(normal * uFreq + uTime * vec3(0.26, 0.32, 0.22));
    float n2 = snoise(normal * uFreq * 2.3 - uTime * vec3(0.21, 0.16, 0.26)) * 0.35;
    vNoise = n1 + n2;
    vec3 p = position + normal * vNoise * uAmp;
    // 光标搅动：命中点附近顶点沿法线涌起，并携带一圈向外扩散的行波
    float dHit = distance(position, uHit);
    float ring = 1.0 - smoothstep(0.05, 0.85, dHit);
    p += normal * ring * uHover * 0.38 * (0.65 + 0.35 * sin(dHit * 7.0 - uTime * 5.0));
    vNormal = normalMatrix * normal;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }`

  const FRAG = /* glsl */ `
  uniform vec3 uColorA; uniform vec3 uColorB; uniform float uBoost;
  varying vec3 vNormal; varying float vNoise;
  void main(){
    vec3 N = normalize(vNormal);
    float light = dot(N, normalize(vec3(0.4, 0.8, 0.6))) * 0.5 + 0.5;
    vec3 base = mix(uColorA, uColorB, smoothstep(-0.6, 0.9, vNoise));
    vec3 col = base * (0.78 + 0.30 * light);
    float fres = pow(1.0 - abs(N.z), 2.4);
    col += fres * vec3(1.0, 0.93, 0.83) * 0.38;
    // 接近感应：光标靠近时提亮并泛出暖光
    col *= 1.0 + 0.22 * uBoost;
    col += uBoost * fres * vec3(1.0, 0.82, 0.66) * 0.18;
    gl_FragColor = vec4(col, 0.97);
  }`

  const makeBlob = (a, b, pos, scale, amp, freq) => {
    const geo = new THREE.IcosahedronGeometry(1, 64)
    const mat = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      transparent: true,
      uniforms: {
        uTime: { value: Math.random() * 10 },
        uAmp: { value: amp },
        uFreq: { value: freq },
        uBoost: { value: 0 },
        uHit: { value: new THREE.Vector3(99, 99, 99) },
        uHover: { value: 0 },
        uColorA: { value: new THREE.Color(a) },
        uColorB: { value: new THREE.Color(b) }
      }
    })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.set(...pos)
    mesh.scale.setScalar(scale)
    mesh.userData.baseY = pos[1]
    mesh.userData.baseAmp = amp
    mesh.userData.baseScale = scale
    scene.add(mesh)
    return mesh
  }

  // 暖色系三球：蜜桃 / 鼠尾草 / 杏杏拿铁
  const blobs = [
    makeBlob('#ffcba8', '#ff9e7a', [-2.6, 0.35, 0], 1.55, 0.30, 1.15),
    makeBlob('#c3d3ae', '#93ab84', [2.7, -0.7, -1.2], 1.18, 0.34, 1.35),
    makeBlob('#f2d3be', '#e2a98f', [0.75, 2.05, -2.4], 0.85, 0.26, 1.5)
  ]

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  let mx = 0, my = 0, tx = 0, ty = 0
  let curX = -9999, curY = -9999 // 光标屏幕像素坐标（接近感应用）
  const ndc = new THREE.Vector2(-2, -2) // 光标 NDC（搅动射线用）
  const onMouse = (e) => {
    tx = (e.clientX / window.innerWidth - 0.5) * 0.9
    ty = -(e.clientY / window.innerHeight - 0.5) * 0.6
    curX = e.clientX
    curY = e.clientY
    ndc.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1)
  }
  if (!reduced) window.addEventListener('mousemove', onMouse, { passive: true })

  const resize = () => {
    const w = window.innerWidth, h = window.innerHeight
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
    camera.position.z = camera.aspect < 1 ? 10.5 : 7.5
  }
  resize()
  window.addEventListener('resize', resize)

  const timer = new THREE.Timer()
  const proj = new THREE.Vector3()
  const raycaster = new THREE.Raycaster()
  const _oc = new THREE.Vector3()
  const _closest = new THREE.Vector3()
  const _hit = new THREE.Vector3()
  const tick = () => {
    timer.update()
    const t = timer.getElapsed()
    const p = window.scrollY / Math.max(window.innerHeight, 1) // 滚动进度（屏数）

    mx += (tx - mx) * 0.035
    my += (ty - my) * 0.035
    camera.position.x = mx
    camera.position.y = my - p * 0.55

    blobs.forEach((m, i) => {
      m.material.uniforms.uTime.value = t + i * 3.7
      m.rotation.y = t * 0.12 + i
      m.rotation.z = Math.sin(t * 0.1 + i) * 0.2
      // 滚动视差：每颗球以不同速率缓缓上浮
      m.position.y = m.userData.baseY + p * (0.85 + i * 0.45)
      m.position.x += Math.sin(t * 0.25 + i * 2.1) * 0.0009

      // 接近感应：球心投到屏幕，与光标距离越近扰动越大、亮度越高
      proj.copy(m.position).project(camera)
      const sx = (proj.x * 0.5 + 0.5) * window.innerWidth
      const sy = (-proj.y * 0.5 + 0.5) * window.innerHeight
      const infl = 170 + m.userData.baseScale * 100
      const targetBoost = Math.max(0, 1 - Math.hypot(curX - sx, curY - sy) / infl)
      const ub = m.material.uniforms.uBoost
      ub.value += (targetBoost - ub.value) * 0.08
      m.material.uniforms.uAmp.value = m.userData.baseAmp * (1 + ub.value * 0.55)

      // 光标搅动：解析法光线-球求交（零遍历开销），命中点转球体局部坐标
      raycaster.setFromCamera(ndc, camera)
      const ray = raycaster.ray
      _oc.subVectors(m.position, ray.origin)
      const tca = _oc.dot(ray.direction)
      _closest.copy(ray.direction).multiplyScalar(tca).add(ray.origin)
      const dSphere = tca > 0 ? _closest.distanceTo(m.position) : Infinity
      const radius = m.userData.baseScale * 1.14 // 含噪声形变余量
      const hitUniform = m.material.uniforms.uHit
      const hoverUniform = m.material.uniforms.uHover
      if (dSphere < radius) {
        m.updateMatrixWorld()
        _hit.copy(_closest)
        m.worldToLocal(_hit)
        hitUniform.value.copy(_hit)
        hoverUniform.value += (Math.max(ub.value, 0.5) - hoverUniform.value) * 0.12
      } else {
        hitUniform.value.set(99, 99, 99)
        hoverUniform.value += (0 - hoverUniform.value) * 0.12
      }
    })

    renderer.render(scene, camera)
    raf = requestAnimationFrame(tick)
  }

  if (reduced) { renderer.render(scene, camera) } else { tick() }

  cleanup = () => {
    cancelAnimationFrame(raf)
    window.removeEventListener('resize', resize)
    window.removeEventListener('mousemove', onMouse)
    blobs.forEach((m) => { m.geometry.dispose(); m.material.dispose() })
    renderer.dispose()
  }
})

onBeforeUnmount(() => cleanup && cleanup())
</script>

<style scoped>
.blob-canvas {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  z-index: 1;
  pointer-events: none;
}
</style>
