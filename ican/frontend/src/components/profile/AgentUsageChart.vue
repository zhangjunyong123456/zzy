<template>
  <div ref="el" class="chart"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import echarts from '../../utils/echarts'

const props = defineProps({
  /** @type {Array<{agent:string,count:number}>} */
  data: { type: Array, default: () => [] }
})

const AGENT_META = [
  { key: 'study', label: '学习', color: '#E8896B' },
  { key: 'research', label: '科研', color: '#93AB84' },
  { key: 'competition', label: '竞赛', color: '#DFA453' },
  { key: 'career', label: '求职', color: '#86AD72' },
  { key: 'campus', label: '校园', color: '#7FB39C' },
  { key: 'main', label: '主控', color: '#D9694A' }
]

const el = ref(null)
let chart = null

function render() {
  if (!chart) return
  const labels = AGENT_META.map((a) => a.label)
  const colors = AGENT_META.map((a) => a.color)
  const counts = AGENT_META.map((a) => props.data.find((d) => d.agent === a.key)?.count ?? 0)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 40, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: 'rgba(233,235,238,.7)' } },
      axisLabel: { color: '#878e99' }
    },
    yAxis: {
      type: 'category',
      data: labels,
      inverse: true,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e9ebee' } },
      axisLabel: { color: '#4e5561' }
    },
    series: [
      {
        type: 'bar',
        data: counts,
        barWidth: 14,
        itemStyle: { color: (p) => colors[p.dataIndex], borderRadius: [0, 7, 7, 0] },
        label: { show: true, position: 'right', color: '#878e99' }
      }
    ]
  })
}

function onResize() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(el.value)
  render()
  window.addEventListener('resize', onResize)
})

watch(() => props.data, render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart { width: 100%; height: 240px; }
</style>
