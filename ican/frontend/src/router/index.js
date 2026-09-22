import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import LandingView from '../views/LandingView.vue'
import ChatView from '../views/ChatView.vue'
import DocsView from '../views/DocsView.vue'
import LoginView from '../views/LoginView.vue'
import ProfileView from '../views/ProfileView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    { path: '/chat', name: 'chat', component: ChatView },
    { path: '/docs', name: 'docs', component: DocsView },
    { path: '/login', name: 'login', component: LoginView },
    // 个人中心不再整页拦截：资料/统计 Tab 内部提示登录，「模型服务」游客也可配置
    { path: '/profile', name: 'profile', component: ProfileView }
  ],
  scrollBehavior() {
    return { top: 0 }
  }
})

// 永不强制跳转登录页：未登录访问需登录页面时，回到主界面并轻提示
router.beforeEach((to) => {
  if (to.meta.requiresAuth && !localStorage.getItem('ug_token')) {
    ElMessage.info('登录后即可完善个人画像，可点击右上角「登录 / 注册」')
    return { path: '/' }
  }
})

export default router
