<template>
  <el-card shadow="never">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>我的知识库</span>
        <el-button text type="primary" @click="store.load()">刷新</el-button>
      </div>
    </template>
    <el-table
      :data="store.docs"
      v-loading="store.loading"
      stripe
      empty-text="暂无文档，上传第一份 PDF 试试 ↓"
    >
      <el-table-column prop="filename" label="文件名" min-width="200" />
      <el-table-column prop="scene" label="场景" width="110">
        <template #default="{ row }">
          {{ sceneLabel(row.scene) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'ready'" type="success" size="small">就绪</el-tag>
          <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
          <el-tag v-else type="info" size="small">解析中</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="pages" label="页数" width="80" />
      <el-table-column prop="chunk_count" label="分块数" width="90" />
      <el-table-column prop="created_at" label="上传时间" width="170">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button text type="danger" size="small" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useDocsStore } from '../../stores/docs'

const store = useDocsStore()
onMounted(() => store.load())

function sceneLabel(s) {
  return { study: '📚 课程资料', research: '🔬 科研论文', career: '💼 简历', campus: '🏫 校园' }[s] || s
}

async function del(row) {
  await ElMessageBox.confirm(`确定删除「${row.filename}」及其向量数据？`, '删除文档', {
    type: 'warning'
  })
  await store.remove(row.id)
  ElMessage.success('已删除')
}
</script>
