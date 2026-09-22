<template>
  <div class="profile-page">
    <div class="profile-wrap">
      <ProfileBanner v-if="userStore.isLoggedIn" />
      <div v-else class="guest-banner">
        <div class="gb-avatar">👤</div>
        <div class="gb-text">
          <div class="gb-title">游客模式</div>
          <div class="gb-sub">登录后可使用个人画像与数据统计；「模型服务」无需登录即可配置</div>
        </div>
        <el-button type="primary" plain size="small" @click="$router.push('/login')">登录 / 注册</el-button>
      </div>

      <div class="profile-card">
        <el-tabs v-model="activeTab" class="profile-tabs">
          <el-tab-pane label="我的资料" name="profile">
            <template v-if="activeTab === 'profile'">
              <template v-if="userStore.isLoggedIn">
                <p class="hint">完善画像后，AI 会自然地把这些信息融入回答（不会生硬复述）</p>
                <el-form label-position="top" :disabled="loading">
                  <div class="grid-2">
                    <el-form-item label="昵称">
                      <el-input v-model="form.nickname" placeholder="希望 AI 怎么称呼你" maxlength="32" />
                    </el-form-item>
                    <el-form-item label="年级">
                      <el-input v-model="form.grade" placeholder="如：大二 / 研一" maxlength="50" />
                    </el-form-item>
                    <el-form-item label="专业">
                      <el-input v-model="form.major" placeholder="如：计算机科学与技术" maxlength="100" />
                    </el-form-item>
                    <el-form-item label="兴趣爱好">
                      <el-input v-model="form.interests" placeholder="如：篮球、摄影、科幻小说" maxlength="2000" />
                    </el-form-item>
                  </div>
                  <el-form-item label="经历 / 背景">
                    <el-input
                      v-model="form.experience"
                      type="textarea"
                      :rows="3"
                      placeholder="如：参加过挑战杯并获省二等奖；在社团负责宣传；会 Python 和一点前端"
                      maxlength="2000"
                    />
                  </el-form-item>
                  <el-form-item label="发展目标">
                    <el-input
                      v-model="form.goal"
                      type="textarea"
                      :rows="3"
                      placeholder="如：准备考研，同时想参加 iCAN 竞赛积累项目经验"
                      maxlength="2000"
                    />
                  </el-form-item>
                </el-form>

                <div class="actions">
                  <el-button @click="$router.back()">返回</el-button>
                  <el-button type="primary" :loading="loading" @click="save">保存</el-button>
                </div>
              </template>
              <el-empty v-else description="登录后即可完善个人画像，让回答更懂你">
                <el-button type="primary" @click="$router.push('/login')">登录 / 注册</el-button>
              </el-empty>
            </template>
          </el-tab-pane>

          <el-tab-pane label="数据统计" name="stats">
            <template v-if="activeTab === 'stats'">
              <StatsPanel v-if="userStore.isLoggedIn" />
              <el-empty v-else description="登录后即可查看你的使用数据">
                <el-button type="primary" @click="$router.push('/login')">登录 / 注册</el-button>
              </el-empty>
            </template>
          </el-tab-pane>

          <el-tab-pane label="模型服务" name="models">
            <ModelService v-if="activeTab === 'models'" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import ProfileBanner from '../components/profile/ProfileBanner.vue'
import StatsPanel from '../components/profile/StatsPanel.vue'
import ModelService from '../components/profile/ModelService.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const activeTab = ref(route.query.tab === 'models' ? 'models' : 'profile')

// Tab 与 ?tab= 查询参数双向同步（HeaderBar「模型配置」等入口可直达指定 Tab）
watch(activeTab, (t) => {
  router.replace({ query: { ...route.query, tab: t === 'profile' ? undefined : t } })
})

const form = reactive({
  nickname: '',
  major: '',
  grade: '',
  interests: '',
  experience: '',
  goal: ''
})

onMounted(() => {
  const u = userStore.user || {}
  Object.assign(form, {
    nickname: u.nickname || '',
    major: u.major || '',
    grade: u.grade || '',
    interests: u.interests || '',
    experience: u.experience || '',
    goal: u.goal || ''
  })
})

async function save() {
  if (loading.value) return
  loading.value = true
  try {
    await userStore.updateProfile({ ...form })
    ElMessage.success('画像已保存，之后的回答会更贴合你')
  } catch (e) {
    ElMessage.error(e?.detail || e?.message || '保存失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background:
    radial-gradient(600px 300px at 15% 0%, rgba(217, 105, 74, .08), transparent 60%),
    radial-gradient(500px 300px at 90% 100%, rgba(147, 171, 132, .10), transparent 60%),
    var(--bg-page);
  padding: 32px 24px 48px;
}
.profile-wrap {
  width: 880px;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.profile-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: 0 18px 50px rgba(29, 33, 41, .08);
  padding: 20px 30px 28px;
}
.guest-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg-card);
  border: 1px dashed var(--border, #e9ebee);
  border-radius: 20px;
  padding: 18px 24px;
}
.gb-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--bg-page, #faf7f2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.gb-title { font-weight: 600; font-size: 15px; }
.gb-sub { font-size: 12.5px; color: var(--text-sub, #878e99); margin-top: 2px; }
.hint {
  margin: 2px 0 16px;
  font-size: 12.5px;
  color: var(--text-sub);
  line-height: 1.6;
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 18px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}
@media (max-width: 560px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
