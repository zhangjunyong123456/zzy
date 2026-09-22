<template>
  <el-card class="upload-panel" shadow="never">
    <template #header>上传学习资料（PDF，≤20MB / 300页）</template>
    <el-upload
      drag
      accept=".pdf"
      :show-file-list="false"
      :auto-upload="false"
      :on-change="onFile"
    >
      <el-icon size="40"><UploadFilled /></el-icon>
      <div>拖拽 PDF 到此处，或 <em>点击选择文件</em></div>
    </el-upload>
    <div style="margin-top: 12px; display: flex; gap: 12px; align-items: center">
      <el-radio-group v-model="scene">
        <el-radio value="study">📚 课程资料</el-radio>
        <el-radio value="research">🔬 科研论文</el-radio>
        <el-radio value="career">💼 简历</el-radio>
      </el-radio-group>
      <el-tag type="info" effect="plain" size="small">
        上传后即可在对话中向对应 Agent 提问
      </el-tag>
    </div>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useDocsStore } from '../../stores/docs'

const store = useDocsStore()
const scene = ref('study')

async function onFile(file) {
  const raw = file.raw
  if (!raw) return
  if (!raw.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.warning('目前仅支持 PDF 文件')
    return
  }
  ElMessage.info(`正在解析：${raw.name}`)
  const err = await store.upload(raw, scene.value)
  if (err) ElMessage.error(err)
  else ElMessage.success(`${raw.name} 解析完成，现在可以针对它提问了`)
}
</script>
