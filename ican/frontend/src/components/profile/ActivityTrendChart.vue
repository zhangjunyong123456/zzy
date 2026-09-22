<template>
  <div ref="el" class="chart"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import echarts from '../../utils/echarts'

const props = defineProps({
  /** @type {Array<{date:string,count:number}>} 近14天 */
  data: { type: Array, default: () => [] }
})

const el = ref(null)
let chart = null

function render() {
  if (!chart) return
  const pad = (n) => String(n).padStart(2, '0')
  const dates = props.data.map((d) => {
    const [y, m, day] = d.date.split('-')
    return `${pad(Number(m))}-${pad(Number(day))}`
  })
  const counts = props.data.map((d) => d.count)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: '#e9ebee' } },
      axisLabel: { color: '#878e99' }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: 'rgba(233,235,238,.7)' } },
      axisLabel: { color: '#878e99' }
    },
    series: [
      {
        name: '消息数',
        type: 'line',
        smooth: true,
        data: counts,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#d9694a', width: 2.5 },
        itemStyle: { color: '#d9694a' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(217, 105, 74, .22)' },
            { offset: 1, color: 'rgba(217, 105, 74, 0)' }
          ])
        }
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
