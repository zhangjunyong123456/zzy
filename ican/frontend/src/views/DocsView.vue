<template>
  <div class="app-shell">
    <Sidebar />
    <div class="main-col">
      <HeaderBar />
      <div class="docs-page">
        <UploadPanel />
        <DocManager />
      </div>
    </div>
  </div>
</template>

<script setup>
import Sidebar from '../components/layout/Sidebar.vue'
import HeaderBar from '../components/layout/HeaderBar.vue'
import UploadPanel from '../components/docs/UploadPanel.vue'
import DocManager from '../components/docs/DocManager.vue'
</script>
