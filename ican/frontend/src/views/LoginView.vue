<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand" @click="$router.push('/')">
        <span class="logo-dot"></span>
        <h1>UniGrow Agent</h1>
      </div>
      <p class="sub">登录后 AI 会结合你的个人画像，给出更贴合你的成长建议</p>

      <el-tabs v-model="tab" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form @submit.prevent>
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="loginForm.password"
                type="password"
                show-password
                placeholder="密码"
                size="large"
                @keydown.enter="doLogin"
              />
            </el-form-item>
            <el-button
              class="submit-btn"
              type="primary"
              size="large"
              :loading="loading"
              @click="doLogin"
            >
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form @submit.prevent>
            <el-form-item>
              <el-input v-model="regForm.username" placeholder="用户名（3-32 位字母/数字/下划线/中文）" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="regForm.password"
                type="password"
                show-password
                placeholder="密码（至少 6 位）"
                size="large"
              />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.nickname" placeholder="昵称（选填）" size="large" @keydown.enter="doRegister" />
            </el-form-item>
            <el-button
              class="submit-btn"
              type="primary"
              size="large"
              :loading="loading"
              @click="doRegister"
            >
              注册并登录
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="guest-entry">
        <router-link :to="redirect">先逛逛（游客模式）→</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { useChatStore } from '../stores/chat'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const chatStore = useChatStore()

const tab = ref('login')
const loading = ref(false)
const redirect = computed(() => String(route.query.redirect || '/chat'))

const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', password: '', nickname: '' })

function errMsg(e) {
  return e?.detail || e?.message || '请求失败，请重试'
}

async function afterAuth() {
  await chatStore.loadSessions().catch(() => {})
  router.push(redirect.value)
}

async function doLogin() {
  if (!loginForm.username.trim() || !loginForm.password || loading.value) return
  loading.value = true
  try {
    await userStore.login({ ...loginForm })
    ElMessage.success('登录成功')
    await afterAuth()
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  if (!regForm.username.trim() || !regForm.password || loading.value) return
  loading.value = true
  try {
    await userStore.register({ ...regForm })
    ElMessage.success('注册成功，已自动登录')
    await afterAuth()
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(600px 300px at 15% 0%, rgba(217, 105, 74, .08), transparent 60%),
    radial-gradient(500px 300px at 90% 100%, rgba(147, 171, 132, .10), transparent 60%),
    var(--bg-page);
  padding: 24px;
}
.login-card {
  width: 400px;
  max-width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: 0 18px 50px rgba(29, 33, 41, .08);
  padding: 36px 34px 26px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  justify-content: center;
}
.logo-dot {
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 5px rgba(217, 105, 74, .15);
}
.brand h1 { font-size: 22px; margin: 0; letter-spacing: .5px; }
.sub {
  text-align: center;
  font-size: 13px;
  color: var(--text-sub);
  margin: 10px 0 22px;
  line-height: 1.6;
}
.submit-btn { width: 100%; margin-top: 4px; }
.guest-entry { text-align: center; margin-top: 18px; font-size: 13px; }
.guest-entry a { color: var(--text-sub); text-decoration: none; }
.guest-entry a:hover { color: var(--accent); }
</style>
