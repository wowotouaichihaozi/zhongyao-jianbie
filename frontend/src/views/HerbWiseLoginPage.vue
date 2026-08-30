<template>
  <main class="herbwise-login-page">
    <header class="login-topbar">
      <div class="brand-lockup" aria-label="岐黄智境">
        <img src="/qihuang-zhijing-mark-512.png" alt="" />
        <span>
          <strong>岐黄智境</strong>
          <small>中药鉴别 · 中医智慧学习平台</small>
        </span>
      </div>
      <p>AI 赋能中医药教育与个性化学习</p>
    </header>

    <section class="hero-panel">
      <div class="hero-kicker"><i></i><span>以学习画像组织知识，以多智能体连接学习与成长</span><i></i></div>
      <h1>岐黄智境</h1>
      <p class="hero-subtitle">领域知识个性化生成<br />与多智能体协同学习平台</p>

      <div class="feature-grid" aria-label="平台核心能力">
        <article v-for="item in capabilities" :key="item.title" class="feature-item">
          <span class="feature-icon"><component :is="item.icon" :size="22" /></span>
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
          </div>
        </article>
      </div>
    </section>

    <aside ref="authPanelRef" class="login-console auth-modal-panel" aria-label="登录或注册">
      <header class="console-heading">
        <span>统一身份认证</span>
        <h2>{{ activeTab === 'register' ? '创建账号' : role === 'admin' ? '管理端登录' : '用户端登录' }}</h2>
      </header>

      <div class="role-tabs" role="radiogroup" aria-label="选择登录角色">
        <button
          v-for="option in roleOptions"
          :key="option.value"
          type="button"
          :class="{ active: role === option.value }"
          role="radio"
          :aria-checked="role === option.value"
          @click="role = option.value"
        >
          <component :is="option.icon" :size="16" />
          {{ option.label }}
        </button>
      </div>

      <div class="auth-tabs" role="tablist" aria-label="认证方式">
        <button type="button" role="tab" :aria-selected="activeTab === 'login'" :class="{ active: activeTab === 'login' }" @click="activeTab = 'login'">登录</button>
        <button type="button" role="tab" :aria-selected="activeTab === 'register'" :class="{ active: activeTab === 'register' }" @click="activeTab = 'register'">注册</button>
      </div>

      <Transition name="auth-panel" mode="out-in">
        <LoginForm
          v-if="activeTab === 'login'"
          key="login"
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
          key="register"
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
      </Transition>

    </aside>
  </main>
</template>

<script setup>
import { computed, markRaw, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpenCheck, Network, ScanSearch, ShieldCheck, UserRound } from 'lucide-vue-next'
import LoginForm from '../components/auth/LoginForm.vue'
import RegisterForm from '../components/auth/RegisterForm.vue'
import { getLoginCaptcha, loginAdminUser, loginUser, registerUser, sendRegisterEmailCode } from '../services/api.js'
import { readRememberedLoginAccount, rememberLoginAccount, setAuthSession } from '../stores/auth.js'
import { DEFAULT_AUTHENTICATED_PATH, safeInternalRedirect } from '../utils/authRedirect.js'

const route = useRoute()
const authPanelRef = ref(null)
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

const capabilities = [
  { icon: markRaw(ScanSearch), title: '药材智能鉴别', description: '结合图像、三维模型与性状要点开展辨识学习。' },
  { icon: markRaw(Network), title: '个性化学习画像', description: '持续汇总学习证据，形成可更新的十维画像。' },
  { icon: markRaw(BookOpenCheck), title: '多模态资源生成', description: '按学习目标生成题库、课件、导图与视频资源。' },
  { icon: markRaw(ShieldCheck), title: '知识溯源与审核', description: '混合知识库检索、引用核验与智能体质量复审。' },
]

const roleOptions = [
  { value: 'user', label: '用户端', icon: markRaw(UserRound) },
  { value: 'admin', label: '管理端', icon: markRaw(ShieldCheck) },
]

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

watch([activeTab, role], resetFeedback)

function openAuth(tab = 'login') {
  activeTab.value = tab === 'register' ? 'register' : 'login'
  authPanelRef.value?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
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
  if (account.includes('@')) return emailPattern.test(account) ? '' : '请输入正确的邮箱地址'
  return /^[A-Za-z0-9_@.\-\u4e00-\u9fa5]{3,32}$/.test(account)
    ? ''
    : '账号长度需为 3-32 位，可包含中文、字母、数字、下划线、点、@ 或短横线'
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

function redirectAfterAuthentication(target) {
  window.location.replace(target)
}

function startEmailCodeCountdown(seconds = 60) {
  emailCodeCountdown.value = seconds
  if (emailCodeTimer) clearInterval(emailCodeTimer)
  emailCodeTimer = setInterval(() => {
    emailCodeCountdown.value = Math.max(0, emailCodeCountdown.value - 1)
    if (emailCodeCountdown.value === 0) {
      clearInterval(emailCodeTimer)
      emailCodeTimer = null
    }
  }, 1000)
}

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
    const credentials = { username: loginForm.username.trim(), password: loginForm.password }
    if (role.value === 'admin') {
      const loginToken = await loginAdminUser(credentials)
      rememberLoginAccount(credentials.username)
      setMessage('正在进入后台管理...', false)
      redirectAfterAuthentication(getAdminHomeUrl(loginToken))
      return
    }
    const user = await loginUser({
      ...credentials,
      captchaId: captchaId.value,
      captchaAnswer: loginForm.captchaAnswer,
    })
    rememberLoginAccount(credentials.username)
    persistUser(user)
    localStorage.setItem('appMode', 'user')
    setMessage('登录成功，正在进入系统...', false)
    redirectAfterAuthentication(pendingRoute.value || DEFAULT_AUTHENTICATED_PATH)
  } catch (error) {
    const data = error.response?.data || {}
    if (data.captchaRequired) await refreshCaptcha(data)
    setMessage(data.msg || data.message || error.message || '认证失败，请稍后再试')
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
    redirectAfterAuthentication(pendingRoute.value || DEFAULT_AUTHENTICATED_PATH)
  } catch (error) {
    const data = error.response?.data || {}
    setMessage(data.msg || data.message || error.message || '注册失败，请稍后再试')
  } finally {
    authLoading.value = false
  }
}

onMounted(() => {
  document.documentElement.classList.add('herbwise-login-scroll')
  document.body.classList.add('herbwise-login-scroll')
  if (pendingRoute.value) openAuth('login')
})

onUnmounted(() => {
  if (emailCodeTimer) clearInterval(emailCodeTimer)
  document.documentElement.classList.remove('herbwise-login-scroll')
  document.body.classList.remove('herbwise-login-scroll')
})
</script>

<style scoped>
.herbwise-login-page {
  position: relative;
  isolation: isolate;
  min-height: 100vh;
  overflow: hidden;
  color: #153f34;
  background: #faf8ef url('/images/herbwise-login-scene.jpg') center / cover no-repeat;
}

.herbwise-login-page::before {
  position: absolute;
  z-index: -1;
  inset: 0;
  content: "";
  background: linear-gradient(90deg, rgba(255, 253, 244, 0.04), rgba(255, 253, 244, 0.1) 52%, rgba(255, 253, 244, 0.78));
}

.login-topbar {
  position: absolute;
  z-index: 2;
  top: 28px;
  right: 4%;
  left: 4%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-lockup img {
  width: 52px;
  height: 52px;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(26, 75, 58, 0.16);
}

.brand-lockup span { display: grid; gap: 1px; }
.brand-lockup strong,
.hero-panel h1,
.console-heading h2 { font-family: "Noto Serif SC", "Songti SC", SimSun, serif; }
.brand-lockup strong { font-size: 23px; }
.brand-lockup small { color: #53685f; font-size: 11px; }
.login-topbar > p { color: #315548; font-size: 14px; }

.hero-panel {
  position: absolute;
  z-index: 1;
  right: 43%;
  bottom: clamp(68px, 8vh, 108px);
  left: 4%;
  max-width: 900px;
}

.hero-kicker {
  display: grid;
  grid-template-columns: 30px minmax(0, auto) 30px;
  align-items: center;
  justify-content: start;
  gap: 14px;
  color: #164e3f;
  font-size: 13px;
  font-weight: 700;
}
.hero-kicker i { width: 30px; height: 1px; background: #b89047; }
.hero-panel h1 { margin: 20px 0 6px; color: #11513f; font-size: clamp(58px, 5vw, 80px); line-height: 1; }
.hero-subtitle { color: #16604b; font-family: "Noto Serif SC", "Songti SC", SimSun, serif; font-size: clamp(19px, 1.55vw, 25px); line-height: 1.6; font-weight: 650; }

.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 42px;
  border-block: 1px solid rgba(138, 108, 50, 0.28);
}

.feature-item {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 10px;
  min-height: 148px;
  padding: 19px 13px;
  border-right: 1px solid rgba(138, 108, 50, 0.2);
}
.feature-item:last-child { border-right: 0; }
.feature-icon { display: grid; width: 44px; height: 44px; color: #176348; background: rgba(255, 252, 232, 0.76); border: 1px solid rgba(190, 149, 65, 0.32); border-radius: 50%; place-items: center; }
.feature-item strong { display: block; margin: 2px 0 5px; color: #154b3c; font-size: 14px; line-height: 1.4; }
.feature-item p { color: #53685f; font-size: 12px; line-height: 1.65; }

.login-console {
  position: absolute;
  z-index: 3;
  top: 50%;
  right: 4%;
  width: min(36.5vw, 520px);
  max-height: calc(100vh - 72px);
  overflow-y: auto;
  padding: 30px 32px 24px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(194, 166, 111, 0.52);
  border-radius: 8px;
  box-shadow: 0 24px 60px rgba(67, 72, 54, 0.16);
  transform: translateY(-46%);
  backdrop-filter: blur(14px);
}

.console-heading { text-align: center; }
.console-heading > span { color: #9a7839; font-size: 11px; font-weight: 750; }
.console-heading h2 { margin: 7px 0 4px; color: #244f41; font-size: 22px; }

.role-tabs,
.auth-tabs { display: grid; grid-template-columns: 1fr 1fr; }
.role-tabs,
.auth-tabs {
  gap: 4px;
  padding: 4px;
  border: 1px solid #d8dfda;
  border-radius: 6px;
  background: #eef2ef;
}
.role-tabs { margin: 20px 0 12px; }
.auth-tabs { margin-bottom: 17px; }
.role-tabs button,
.auth-tabs button {
  min-height: 40px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #65766f;
  cursor: pointer;
  font-weight: 700;
  transition: background-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}
.role-tabs button { display: flex; align-items: center; justify-content: center; gap: 7px; }
.role-tabs button:hover,
.auth-tabs button:hover { color: #174c3c; background: rgba(255, 255, 255, 0.7); }
:global(#app .herbwise-login-page .role-tabs button.active),
:global(#app .herbwise-login-page .auth-tabs button.active) {
  color: #fff !important;
  background: #174c3c !important;
  box-shadow: 0 3px 10px rgba(23, 76, 60, 0.2);
}

:global(#app .herbwise-login-page .password-field) {
  position: relative;
}

:global(#app .herbwise-login-page .password-field input) {
  padding-right: 48px !important;
}

:global(#app .herbwise-login-page .password-field .password-visibility-toggle),
:global(#app .herbwise-login-page .password-field .password-visibility-toggle:hover),
:global(#app .herbwise-login-page .password-field .password-visibility-toggle:focus),
:global(#app .herbwise-login-page .password-field .password-visibility-toggle:active) {
  position: absolute !important;
  z-index: 2;
  top: 50% !important;
  right: 11px !important;
  bottom: auto !important;
  left: auto !important;
  display: grid !important;
  width: 30px !important;
  min-width: 30px !important;
  height: 30px !important;
  min-height: 30px !important;
  margin: 0 !important;
  padding: 0 !important;
  place-items: center;
  border: 0 !important;
  border-radius: 50% !important;
  background: transparent !important;
  color: #64748b !important;
  box-shadow: none !important;
  transform: translateY(-50%) !important;
}

:global(#app .herbwise-login-page .password-field .password-visibility-toggle:hover) {
  color: #174c3c !important;
}

:global(#app .herbwise-login-page .password-field .password-visibility-toggle:focus-visible) {
  outline: 2px solid rgba(23, 76, 60, 0.32) !important;
  outline-offset: -2px;
}

.login-console :deep(form) { gap: 12px; }
.login-console :deep(label > span:first-child) { margin-bottom: 5px; color: #345548; font-size: 12px; }
.login-console :deep(input) { height: 50px; border-radius: 6px; background: rgba(248, 251, 249, 0.92); }
.login-console :deep(.auth-primary-action) { height: 50px; border-radius: 6px; background: #1d674e; box-shadow: 0 12px 24px rgba(29, 103, 78, 0.18); font-family: "Noto Serif SC", "Songti SC", SimSun, serif; font-size: 16px; }
.login-console :deep(.auth-primary-action:hover) { background: #15563f; }
.login-console :deep(form > p:last-child) { display: none; }

.auth-panel-enter-active,
.auth-panel-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.auth-panel-enter-from,
.auth-panel-leave-to { opacity: 0; transform: translateY(4px); }

@media (max-width: 1180px) {
  .login-console { right: 3%; width: min(42vw, 500px); }
  .hero-panel { right: 47%; left: 3%; }
  .feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .feature-item { min-height: 108px; }
  .feature-item:nth-child(2) { border-right: 0; }
  .feature-item:nth-child(-n + 2) { border-bottom: 1px solid rgba(138, 108, 50, 0.2); }
}

@media (max-width: 860px) {
  .herbwise-login-page { min-height: 100dvh; overflow: auto; padding: 94px 20px 28px; background-position: 32% center; }
  .herbwise-login-page::before { background: rgba(255, 253, 244, 0.84); }
  .login-topbar { top: 18px; right: 20px; left: 20px; }
  .login-topbar > p { display: none; }
  .brand-lockup img { width: 46px; height: 46px; }
  .hero-panel { position: relative; right: auto; bottom: auto; left: auto; max-width: 520px; margin: 0 auto 20px; }
  .hero-kicker,
  .feature-grid { display: none; }
  .hero-panel h1 { margin: 0 0 5px; font-size: 42px; }
  .hero-subtitle { font-size: 15px; }
  .login-console { position: relative; top: auto; right: auto; width: min(100%, 520px); max-height: none; margin: 0 auto; padding: 26px 22px 22px; transform: none; }
}

@media (max-width: 420px) {
  .herbwise-login-page { padding-inline: 14px; }
  .brand-lockup strong { font-size: 20px; }
  .brand-lockup small { font-size: 10px; }
  .hero-panel h1 { font-size: 36px; }
  .login-console { padding-inline: 18px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
}
</style>
