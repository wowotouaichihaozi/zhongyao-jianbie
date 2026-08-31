<template>
  <main class="archify-login-shell">
    <iframe
      class="archify-login-frame"
      src="/archify/index.html"
      title="项目介绍"
      @load="frameReady = true"
    />

    <div v-if="authModalOpen" class="archify-auth-backdrop" role="dialog" aria-modal="true" aria-label="登录或注册">
      <section class="archify-auth-modal">
        <button class="archify-auth-close" type="button" aria-label="关闭登录窗口" @click="closeAuth"><X :size="20" /></button>
        <header><strong>{{ activeTab === 'register' ? '创建账号' : role === 'admin' ? '管理端登录' : '用户端登录' }}</strong><span>登录后进入中药鉴别学习系统</span></header>
        <RoleSelector v-if="activeTab === 'login'" v-model="role" class="archify-role-selector" />
        <TabSwitch v-model="activeTab" class="mb-5" />
        <LoginForm v-if="activeTab === 'login'" :form="loginForm" :loading="authLoading" :message="authMessage" :error="authError" :captcha-required="captchaRequired" :captcha-question="captchaQuestion" @submit="submitLogin" />
        <RegisterForm v-else :form="registerForm" :loading="authLoading" :message="authMessage" :error="authError" :email-valid="isRegisterEmailValid" :email-code-sending="emailCodeSending" :email-code-countdown="emailCodeCountdown" :password-strength="passwordStrength" @submit="submitRegister" @send-email-code="sendEmailCode" />
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { X } from 'lucide-vue-next'
import LoginForm from '../components/auth/LoginForm.vue'
import RegisterForm from '../components/auth/RegisterForm.vue'
import RoleSelector from '../components/auth/RoleSelector.vue'
import TabSwitch from '../components/auth/TabSwitch.vue'
import { getLoginCaptcha, loginAdminUser, loginUser, registerUser, sendRegisterEmailCode } from '../services/api.js'
import { readRememberedLoginAccount, rememberLoginAccount, setAuthSession } from '../stores/auth.js'
import { DEFAULT_AUTHENTICATED_PATH, safeInternalRedirect } from '../utils/authRedirect.js'

const route = useRoute()
const frameReady = ref(false)
const authModalOpen = ref(false)
const activeTab = ref('login')
const role = ref(route.query.role === 'admin' ? 'admin' : 'user')
const authLoading = ref(false)
const authMessage = ref('')
const authError = ref(false)
const captchaRequired = ref(false)
const captchaId = ref('')
const captchaQuestion = ref('')
const emailCodeSending = ref(false)
const emailCodeCountdown = ref(0)
const pendingRoute = safeInternalRedirect(route.query.redirect)
let emailCodeTimer = null

const loginForm = reactive({ username: readRememberedLoginAccount(), password: '', captchaAnswer: '' })
const registerForm = reactive({ username: '', displayName: '', email: '', emailCode: '', password: '', confirmPassword: '', acceptTerms: false })
const emailPattern = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/
const isRegisterEmailValid = computed(() => emailPattern.test(registerForm.email.trim()))
const passwordStrength = computed(() => ({ label: registerForm.password.length >= 10 ? '强' : registerForm.password.length >= 8 ? '中' : '弱', level: registerForm.password.length >= 10 ? 'strong' : registerForm.password.length >= 8 ? 'medium' : 'weak' }))

function openAuth(tab = 'login') { activeTab.value = tab; authModalOpen.value = true }
function closeAuth() { if (!authLoading.value) authModalOpen.value = false }
function setMessage(message, error = true) { authMessage.value = message; authError.value = error }
function resetFeedback() { setMessage('', false); captchaRequired.value = false; captchaId.value = ''; captchaQuestion.value = ''; loginForm.captchaAnswer = '' }
function validateAccount(value) { if (!value.trim()) return '请输入账号'; return value.includes('@') && !emailPattern.test(value.trim()) ? '请输入正确的邮箱地址' : '' }
function getAdminBaseUrl() {
  if (import.meta.env.DEV) {
    const hostname = window.location.hostname || '127.0.0.1'
    return `${window.location.protocol}//${hostname}:9527`
  }
  return `${window.location.origin}/admin`
}
function getAdminHomeUrl(loginToken) {
  const token = loginToken?.token || ''
  const refreshToken = loginToken?.refreshToken || token
  if (!token) return `${getAdminBaseUrl()}/login`
  const params = new URLSearchParams({ auth_token: token, refresh_token: refreshToken, redirect: '/dashboard' })
  return `${getAdminBaseUrl()}/dashboard#${params.toString()}`
}
async function submitLogin() {
  const accountError = validateAccount(loginForm.username)
  if (accountError || loginForm.password.length < 8) return setMessage(accountError || '密码至少 8 位')
  authLoading.value = true; setMessage('', false)
  try {
    const credentials = { username: loginForm.username.trim(), password: loginForm.password }
    if (role.value === 'admin') {
      const loginToken = await loginAdminUser(credentials)
      rememberLoginAccount(credentials.username)
      window.location.replace(getAdminHomeUrl(loginToken))
      return
    }
    const user = await loginUser({ username: loginForm.username.trim(), password: loginForm.password, captchaId: captchaId.value, captchaAnswer: loginForm.captchaAnswer })
    rememberLoginAccount(loginForm.username); setAuthSession({ ...user, avatarUrl: user.avatarUrl || '/userlogo.png' }); localStorage.setItem('appMode', 'user'); window.location.replace(pendingRoute || DEFAULT_AUTHENTICATED_PATH)
  } catch (error) {
    const data = error.response?.data || {}
    if (data.captchaRequired) { captchaRequired.value = true; captchaId.value = data.captchaId || ''; captchaQuestion.value = data.question || ''; if (!captchaQuestion.value) { const captcha = await getLoginCaptcha(); captchaId.value = captcha.captchaId; captchaQuestion.value = captcha.question } }
    setMessage(data.msg || data.message || error.message || '登录失败，请稍后再试')
  } finally { authLoading.value = false }
}
async function sendEmailCode() {
  if (!isRegisterEmailValid.value) return setMessage('请输入正确的邮箱地址')
  emailCodeSending.value = true
  try { const result = await sendRegisterEmailCode({ email: registerForm.email.trim() }); setMessage(result.msg || '验证码已发送，请查收邮箱', false); emailCodeCountdown.value = 60; emailCodeTimer = setInterval(() => { emailCodeCountdown.value -= 1; if (emailCodeCountdown.value <= 0) clearInterval(emailCodeTimer) }, 1000) } catch (error) { setMessage(error.response?.data?.msg || '验证码发送失败') } finally { emailCodeSending.value = false }
}
async function submitRegister() {
  if (validateAccount(registerForm.username) || !registerForm.displayName.trim() || !isRegisterEmailValid.value || !registerForm.emailCode.trim() || registerForm.password.length < 8 || registerForm.password !== registerForm.confirmPassword || !registerForm.acceptTerms) return setMessage('请完整填写注册信息并确认密码、同意协议')
  authLoading.value = true; setMessage('', false)
  try { const user = await registerUser({ username: registerForm.username.trim(), displayName: registerForm.displayName.trim(), email: registerForm.email.trim(), emailCode: registerForm.emailCode.trim(), password: registerForm.password }); rememberLoginAccount(registerForm.username); setAuthSession({ ...user, avatarUrl: user.avatarUrl || '/userlogo.png' }); window.location.replace(pendingRoute || DEFAULT_AUTHENTICATED_PATH) } catch (error) { setMessage(error.response?.data?.msg || '注册失败，请稍后再试') } finally { authLoading.value = false }
}
function onMessage(event) { if (event.origin === window.location.origin && event.data?.type === 'archify-login') openAuth('login') }
watch([activeTab, role], resetFeedback)
onMounted(() => { window.addEventListener('message', onMessage); if (pendingRoute) openAuth('login') })
onUnmounted(() => { window.removeEventListener('message', onMessage); if (emailCodeTimer) clearInterval(emailCodeTimer) })
</script>

<style scoped>
.archify-login-shell { min-height: 100vh; background: #eff2f1; }
.archify-login-frame { display: block; width: 100%; height: 100vh; border: 0; }
.archify-auth-backdrop { position: fixed; inset: 0; z-index: 20; display: grid; place-items: center; padding: 1rem; background: rgba(21,24,27,.42); backdrop-filter: blur(8px); }
.archify-auth-modal { position: relative; width: min(100%, 540px); max-height: calc(100vh - 2rem); overflow: auto; padding: 2rem; border: 1px solid rgba(255,255,255,.75); border-radius: 18px; background: rgba(248,250,249,.96); box-shadow: 0 24px 80px rgba(21,24,27,.24); }
.archify-auth-modal header { margin-bottom: 1.4rem; text-align: center; }
.archify-auth-modal header strong, .archify-auth-modal header span { display: block; }
.archify-auth-modal header strong { font: 600 1.5rem/1.2 'Space Grotesk', sans-serif; }
.archify-auth-modal header span { margin-top: .4rem; color: #60686d; font-size: .84rem; }
.archify-role-selector { margin-bottom: 1rem; }
.archify-auth-modal :deep(.auth-role-option) { min-height: 50px; border-radius: 7px; box-shadow: none; transform: none; }
.archify-auth-modal :deep(.auth-role-option:hover) { transform: none; }
.archify-auth-modal :deep(.auth-role-option-active) { border-color: #6ea78f !important; background: #e8f3ed !important; box-shadow: inset 0 0 0 1px rgba(23, 107, 82, .08) !important; }
.archify-auth-modal :deep(.auth-role-option.auth-role-option-active),
.archify-auth-modal :deep(.auth-role-option.auth-role-option-active span),
.archify-auth-modal :deep(.auth-role-option.auth-role-option-active svg) { color: #176b52 !important; }
.archify-auth-modal :deep(.auth-role-option-active > span:first-child) { background: #f7fbf9 !important; color: #176b52 !important; }
.archify-auth-modal :deep(.auth-role-option-active > span:last-child) { display: none; }
.archify-auth-close { position: absolute; top: .8rem; right: .8rem; display: grid; width: 2rem; height: 2rem; place-items: center; border: 0; border-radius: 6px; background: transparent; color: #60686d; cursor: pointer; }
.archify-auth-close:hover { background: #e7ecea; color: #15181b; }
.archify-auth-modal :deep(.password-field) { position: relative !important; display: grid !important; min-height: 56px; }
.archify-auth-modal :deep(.password-field input) { height: 56px !important; padding-right: 52px !important; }
.archify-auth-modal :deep(.password-field .password-visibility-toggle),
.archify-auth-modal :deep(.password-field .password-visibility-toggle:hover),
.archify-auth-modal :deep(.password-field .password-visibility-toggle:focus),
.archify-auth-modal :deep(.password-field .password-visibility-toggle:focus-visible),
.archify-auth-modal :deep(.password-field .password-visibility-toggle:active) {
  position: relative !important;
  z-index: 3 !important;
  grid-area: 1 / 1 !important;
  align-self: center !important;
  justify-self: end !important;
  display: grid !important;
  width: 34px !important;
  min-width: 34px !important;
  height: 34px !important;
  min-height: 34px !important;
  margin: 0 10px 0 0 !important;
  padding: 0 !important;
  place-items: center !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  outline: 0 !important;
  appearance: none !important;
  -webkit-appearance: none !important;
  transform: none !important;
}
.archify-auth-modal :deep(.password-field .password-visibility-toggle svg) { display: block; width: 18px; height: 18px; transform: none !important; }
@media (max-width: 700px) { .archify-login-frame { height: 100svh; } .archify-auth-modal { padding: 1.25rem; border-radius: 12px; } }
</style>
