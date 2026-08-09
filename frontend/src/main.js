import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles.css'
import './styles/apimart-theme.css'

const CLIENT_DATA_VERSION_KEY = 'feishengwangying:client-data-version'
const CLIENT_DATA_VERSION = 'token-auth-v1'
const CODEX_PREVIEW_AUTH_KEY = 'codexPreviewAuth'

if (localStorage.getItem(CLIENT_DATA_VERSION_KEY) !== CLIENT_DATA_VERSION) {
  Object.keys(localStorage)
    .filter((key) =>
      key.startsWith('feishengwangying:last-analysis-session-id')
    )
    .forEach((key) => localStorage.removeItem(key))
  localStorage.setItem(CLIENT_DATA_VERSION_KEY, CLIENT_DATA_VERSION)
}

if (['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)) {
  const currentUrl = new URL(window.location.href)
  if (currentUrl.searchParams.get('codexPreview') === '1') {
    localStorage.setItem(CODEX_PREVIEW_AUTH_KEY, '1')
  }
}

createApp(App).use(router).mount('#app')
