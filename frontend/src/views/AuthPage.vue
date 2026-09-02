<template>
  <main class="auth-page">
    <section class="auth-layout" aria-label="嵌智学航登录">
      <div class="auth-intro">
        <div class="auth-brand">
          <span class="auth-brand-mark" aria-hidden="true">
            <Cpu :size="29" :stroke-width="1.8" />
          </span>
          <span>
            <strong>嵌智学航</strong>
            <small>智能学习 · 智慧未来</small>
          </span>
        </div>

        <div class="auth-intro-copy">
          <p class="auth-eyebrow">嵌入式个性化学习平台</p>
          <h1>让学习路径更清晰，<br />让实践过程有依据。</h1>
          <p>围绕学习画像、个性化资源与嵌入式实验，持续记录并优化每一步学习。</p>
        </div>

        <figure class="auth-visual">
          <picture>
            <source srcset="/auth-hero-embedded-collage.webp" type="image/webp" />
            <img
              src="/auth-hero-embedded-collage.png"
              alt="示波器、开发板、机器人与数字人组成的嵌入式学习场景"
              decoding="async"
              fetchpriority="high"
            />
          </picture>
        </figure>
      </div>

      <div class="auth-panel-wrap">
        <section class="auth-panel" :class="{ 'auth-panel-register': activeTab === 'register' }">
          <header class="auth-panel-header">
            <span class="auth-panel-icon" aria-hidden="true">
              <GraduationCap :size="27" :stroke-width="1.9" />
            </span>
            <div>
              <h2>{{ activeTab === 'login' ? '欢迎回来' : '创建账号' }}</h2>
              <p>{{ activeTab === 'login' ? '登录后继续你的学习计划' : '注册后即可开始个性化学习' }}</p>
            </div>
          </header>

          <RoleSelector v-model="role" :class="activeTab === 'register' ? 'mb-2.5' : 'mb-5'" />
          <TabSwitch v-model="activeTab" :class="activeTab === 'register' ? 'mb-2.5' : 'mb-5'" />

          <LoginForm
            v-if="activeTab === 'login'"
            :form="loginForm"
            :loading="authLoading"
            :message="authMessage"
            :error="authError"
            :captcha-required="captchaRequired"
            :captcha-question="captchaQuestion"
            @submit="submitLogin"
          />
          <RegisterForm
            v-else
            :form="registerForm"
            :loading="authLoading"
            :message="authMessage"
            :error="authError"
            :email-valid="isRegisterEmailValid"
            :email-code-sending="emailCodeSending"
            :email-code-countdown="emailCodeCountdown"
            :password-strength="passwordStrength"
            @submit="submitRegister"
            @send-email-code="sendEmailCode"
          />
        </section>

        <p class="auth-record">
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">赣ICP备2026009448号-1</a>
        </p>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Cpu, GraduationCap } from 'lucide-vue-next'
import LoginForm from '../components/auth/LoginForm.vue'
import RegisterForm from '../components/auth/RegisterForm.vue'
import RoleSelector from '../components/auth/RoleSelector.vue'
import TabSwitch from '../components/auth/TabSwitch.vue'
import { getLoginCaptcha, loginAdminUser, loginUser, registerUser, sendRegisterEmailCode } from '../services/api.js'
import { readRememberedLoginAccount, rememberLoginAccount, setAuthSession } from '../stores/auth.js'
import { DEFAULT_AUTHENTICATED_PATH, safeInternalRedirect } from '../utils/authRedirect.js'

const router = useRouter()
const route = useRoute()

const activeTab = ref('login')
const role = ref(route.query.role === 'admin' ? 'admin' : 'user')
const authLoading = ref(false)
const authMessage = ref('')
const authError = ref(false)
const captchaRequired = ref(false)
const captchaId = ref('')
const captchaQuestion = ref('')
const pendingRoute = ref(safeInternalRedirect(route.query.redirect))
const emailCodeSending = ref(false)
const emailCodeCountdown = ref(0)
let emailCodeTimer = null

const loginForm = reactive({
  username: readRememberedLoginAccount(),
  password: '',
  captchaAnswer: '',
})

const registerForm = reactive({
  username: '',
  displayName: '',
  email: '',
  emailCode: '',
  password: '',
  confirmPassword: '',
  acceptTerms: false,
})

const emailPattern = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/

const isRegisterEmailValid = computed(() => emailPattern.test(registerForm.email.trim()))

const passwordStrength = computed(() => {
  const password = registerForm.password || ''
  let score = 0
  if (password.length >= 8) score += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password)) score += 1
  if (score >= 4) return { label: '强', level: 'strong' }
  if (score >= 2) return { label: '中', level: 'medium' }
  return { label: '弱', level: 'weak' }
})

watch([activeTab, role], () => {
  resetFeedback()
})

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

  const params = new URLSearchParams({
    auth_token: token,
    refresh_token: refreshToken,
    redirect: '/dashboard',
  })

  return `${getAdminBaseUrl()}/dashboard#${params.toString()}`
}

function resetFeedback() {
  authMessage.value = ''
  authError.value = false
  captchaRequired.value = false
  captchaId.value = ''
  captchaQuestion.value = ''
  loginForm.captchaAnswer = ''
}

function setMessage(message, isError = true) {
  authMessage.value = message
  authError.value = isError
}

function validateAccount(value) {
  const account = value.trim()
  if (!account) return '请输入账号'
  if (account.includes('@')) {
    return emailPattern.test(account) ? '' : '请输入正确的邮箱地址'
  }
  if (!/^[A-Za-z0-9_@.\-\u4e00-\u9fa5]{3,32}$/.test(account)) {
    return '账号长度需为 3-32 位，可包含中文、字母、数字、下划线、点、@ 或短横线'
  }
  return ''
}

function validateLogin() {
  const accountError = validateAccount(loginForm.username)
  if (accountError) return accountError
  if (!loginForm.password || loginForm.password.length < 8) return '密码至少 8 位'
  if (captchaRequired.value && !loginForm.captchaAnswer) return '请输入验证码'
  return ''
}

function validateRegister() {
  const accountError = validateAccount(registerForm.username)
  if (accountError) return accountError
  if (!registerForm.displayName.trim()) return '请输入昵称'
  if (!isRegisterEmailValid.value) return '请输入正确的邮箱地址'
  if (!registerForm.emailCode.trim()) return '请输入邮箱验证码'
  if (!registerForm.password || registerForm.password.length < 8) return '密码至少 8 位'
  if (passwordStrength.value.level === 'weak') return '密码强度过弱，请增加数字、大小写字母或符号'
  if (registerForm.password !== registerForm.confirmPassword) return '两次输入的密码不一致'
  if (!registerForm.acceptTerms) return '注册前请先同意用户协议与隐私政策'
  return ''
}

function persistUser(user) {
  setAuthSession({ ...user, avatarUrl: user.avatarUrl || '/userlogo.png' })
}

async function refreshCaptcha(payload = {}) {
  captchaRequired.value = true
  captchaId.value = payload.captchaId || ''
  captchaQuestion.value = payload.question || ''
  if (!captchaId.value || !captchaQuestion.value) {
    const captcha = await getLoginCaptcha()
    captchaId.value = captcha.captchaId
    captchaQuestion.value = captcha.question
  }
  loginForm.captchaAnswer = ''
}

function startEmailCodeCountdown(seconds = 60) {
  emailCodeCountdown.value = seconds
  if (emailCodeTimer) clearInterval(emailCodeTimer)
  emailCodeTimer = setInterval(() => {
    emailCodeCountdown.value = Math.max(0, emailCodeCountdown.value - 1)
    if (emailCodeCountdown.value === 0 && emailCodeTimer) {
      clearInterval(emailCodeTimer)
      emailCodeTimer = null
    }
  }, 1000)
}

onUnmounted(() => {
  if (emailCodeTimer) clearInterval(emailCodeTimer)
})

async function sendEmailCode() {
  if (!isRegisterEmailValid.value) {
    setMessage('请输入正确的邮箱地址')
    return
  }

  emailCodeSending.value = true
  setMessage('', false)
  try {
    const result = await sendRegisterEmailCode({ email: registerForm.email.trim() })
    setMessage(result.msg || '验证码已发送，请查收邮箱', false)
    startEmailCodeCountdown(60)
  } catch (error) {
    const data = error.response?.data || {}
    setMessage(data.msg || data.message || '验证码发送失败，请稍后再试')
  } finally {
    emailCodeSending.value = false
  }
}

async function submitLogin() {
  const validation = validateLogin()
  if (validation) {
    setMessage(validation)
    return
  }

  authLoading.value = true
  setMessage('', false)
  try {
    const credentials = {
      username: loginForm.username.trim(),
      password: loginForm.password,
    }

    if (role.value === 'admin') {
      const loginToken = await loginAdminUser(credentials)
      rememberLoginAccount(credentials.username)
      setMessage('正在进入后台管理...', false)
      window.location.href = getAdminHomeUrl(loginToken)
      return
    }

    const user = await loginUser({
      ...credentials,
      captchaId: captchaId.value,
      captchaAnswer: loginForm.captchaAnswer,
    })
    rememberLoginAccount(credentials.username)
    persistUser(user)
    localStorage.setItem('appMode', role.value)
    setMessage('登录成功，正在进入系统...', false)
    await router.replace(pendingRoute.value || DEFAULT_AUTHENTICATED_PATH)
  } catch (error) {
    const data = error.response?.data || {}
    if (data.captchaRequired) await refreshCaptcha(data)
    setMessage(data.msg || data.message || '认证失败，请稍后再试')
  } finally {
    authLoading.value = false
  }
}

async function submitRegister() {
  const validation = validateRegister()
  if (validation) {
    setMessage(validation)
    return
  }

  authLoading.value = true
  setMessage('', false)
  try {
    const user = await registerUser({
      username: registerForm.username.trim(),
      displayName: registerForm.displayName.trim(),
      email: registerForm.email.trim(),
      emailCode: registerForm.emailCode.trim(),
      password: registerForm.password,
    })
    rememberLoginAccount(registerForm.username)
    persistUser(user)
    localStorage.setItem('appMode', 'user')
    setMessage('注册成功，正在进入系统...', false)
    await router.replace(pendingRoute.value || DEFAULT_AUTHENTICATED_PATH)
  } catch (error) {
    const data = error.response?.data || {}
    setMessage(data.msg || data.message || '注册失败，请稍后再试')
  } finally {
    authLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 24px;
  background: #f4f7f6;
  color: #1e293b;
}

.auth-layout {
  width: min(1180px, 100%);
  min-height: min(720px, calc(100dvh - 48px));
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(440px, 0.85fr);
  overflow: hidden;
  border: 1px solid #e2e8e6;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 20px 55px rgba(15, 23, 42, 0.1);
}

.auth-intro {
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: 42px 44px 38px;
  overflow: hidden;
  border-right: 1px solid #e8eeec;
  background: #eef7f4;
}

.auth-brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-brand-mark,
.auth-panel-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  color: #047857;
  background: #ffffff;
  border: 1px solid #cce8df;
}

.auth-brand-mark {
  width: 48px;
  height: 48px;
  border-radius: 8px;
}

.auth-brand strong,
.auth-brand small {
  display: block;
  letter-spacing: 0;
}

.auth-brand strong {
  color: #065f46;
  font-size: 25px;
  line-height: 1.2;
}

.auth-brand small {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}

.auth-intro-copy {
  position: relative;
  z-index: 1;
  margin-top: 56px;
  max-width: 500px;
}

.auth-eyebrow {
  margin: 0 0 12px;
  color: #047857;
  font-size: 14px;
  font-weight: 700;
}

.auth-intro-copy h1 {
  margin: 0;
  color: #17233c;
  font-size: clamp(32px, 3.1vw, 46px);
  line-height: 1.28;
  letter-spacing: 0;
}

.auth-intro-copy > p:last-child {
  max-width: 460px;
  margin: 18px 0 0;
  color: #64748b;
  font-size: 16px;
  line-height: 1.8;
}

.auth-visual {
  position: relative;
  flex: 1 1 auto;
  min-height: 250px;
  margin: 32px 0 0;
  overflow: hidden;
  border-radius: 6px;
  background: #ffffff;
}

.auth-visual,
.auth-visual picture,
.auth-visual img {
  width: 100%;
}

.auth-visual picture,
.auth-visual img {
  display: block;
  height: 100%;
}

.auth-visual img {
  object-fit: cover;
  object-position: center;
}

.auth-panel-wrap {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  padding: 34px 44px 20px;
  background: #ffffff;
}

.auth-panel {
  width: 100%;
  max-width: 460px;
  margin: auto;
}

.auth-panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.auth-panel-register .auth-panel-header {
  margin-bottom: 12px;
}

.auth-panel-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: #ecfdf5;
}

.auth-panel-header h2 {
  margin: 0;
  color: #17233c;
  font-size: 25px;
  line-height: 1.25;
  letter-spacing: 0;
}

.auth-panel-header p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.auth-record {
  margin: 22px 0 0;
  text-align: center;
  font-size: 12px;
}

.auth-record a {
  color: #94a3b8;
  text-decoration: none;
}

.auth-record a:hover,
.auth-record a:focus-visible {
  color: #047857;
}

@media (max-width: 900px) {
  .auth-page {
    overflow: auto;
    padding: 16px;
  }

  .auth-layout {
    min-height: calc(100dvh - 32px);
    grid-template-columns: 1fr;
  }

  .auth-intro {
    min-height: auto;
    padding: 24px 28px;
    border-right: 0;
    border-bottom: 1px solid #e8eeec;
  }

  .auth-intro-copy {
    margin-top: 20px;
  }

  .auth-intro-copy h1 {
    font-size: 30px;
  }

  .auth-intro-copy > p:last-child,
  .auth-visual {
    display: none;
  }

  .auth-panel-wrap {
    padding: 28px;
  }
}

@media (max-width: 520px) {
  .auth-page {
    padding: 0;
    background: #ffffff;
  }

  .auth-layout {
    min-height: 100dvh;
    border: 0;
    border-radius: 0;
    box-shadow: none;
  }

  .auth-intro {
    padding: 18px 20px;
  }

  .auth-intro-copy {
    display: none;
  }

  .auth-brand-mark {
    width: 42px;
    height: 42px;
  }

  .auth-brand strong {
    font-size: 21px;
  }

  .auth-panel-wrap {
    justify-content: flex-start;
    padding: 24px 20px 16px;
  }

  .auth-panel-header {
    margin-bottom: 18px;
  }

  .auth-panel-register .auth-panel-header {
    display: none;
  }

  .auth-panel-header h2 {
    font-size: 22px;
  }

  .auth-record {
    margin-top: 18px;
  }
}

@media (max-height: 740px) and (min-width: 901px) {
  .auth-page {
    padding: 12px;
  }

  .auth-layout {
    min-height: calc(100dvh - 24px);
  }

  .auth-intro {
    padding: 28px 34px;
  }

  .auth-intro-copy {
    margin-top: 30px;
  }

  .auth-visual {
    margin-top: 22px;
  }

  .auth-panel-wrap {
    padding-top: 20px;
    padding-bottom: 12px;
  }

  .auth-record {
    margin-top: 10px;
  }
}
</style>
