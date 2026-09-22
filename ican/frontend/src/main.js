import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './styles/main.css'
import { registerProx, unregisterProx } from './utils/proximity'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// v-prox 接近感应指令：鼠标靠近时写入 --prox / --px / --py 供样式消费
app.directive('prox', {
  mounted(el, binding) {
    registerProx(el, binding.value || {})
  },
  unmounted(el) {
    unregisterProx(el)
  }
})

app.mount('#app')
