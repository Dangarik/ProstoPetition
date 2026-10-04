import { createApp } from 'vue'
import 'bootstrap/dist/css/bootstrap.min.css'
import './styles.css'
import App from './App.vue'
import router from './router.js'
import { ensureSession } from './session.js'

ensureSession().finally(() => {
  createApp(App).use(router).mount('#app')
})

