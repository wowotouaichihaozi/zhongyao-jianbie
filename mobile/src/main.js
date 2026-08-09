import { createApp } from 'vue'
import { registerSW } from 'virtual:pwa-register'
import App from './App.vue'
import router from './router/index.js'
import './styles.css'

registerSW({ immediate: false })

createApp(App).use(router).mount('#app')
