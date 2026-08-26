<template>
  <main class="auth-entry-page">
    <div class="auth-subtle-bg" aria-hidden="true"></div>
    <div class="auth-line-bg" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
      <span></span>
    </div>
    <div class="auth-line-nodes" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
      <span></span>
      <span></span>
      <span></span>
    </div>

    <section class="auth-entry-card">
      <div class="auth-entry-brand">
        <img src="/logo.png" alt="岐黄智境" />
      </div>

      <div class="auth-portal-switch" role="tablist" aria-label="登录入口">
        <button
          type="button"
          :class="{ active: portalMode === 'user' }"
          role="tab"
          :aria-selected="portalMode === 'user'"
          @click="setPortal('user')"
        >
          <span>用户端</span>
          <small>学习平台</small>
        </button>
        <button
          type="button"
          :class="{ active: portalMode === 'admin' }"
          role="tab"
          :aria-selected="portalMode === 'admin'"
          @click="setPortal('admin')"
        >
          <span>管理员端</span>
          <small>后台管理</small>
        </button>
      </div>

      <div class="auth-card-head">
        <div class="auth-mode-switch">
          <button type="button" :class="{ active: !isRegisterMode }" @click="setMode('login')">
            登录
          </button>
          <button type="button" :class="{ active: isRegisterMode }" @click="setMode('register')">
            注册
          </button>
        </div>
      </div>

      <form
        class="auth-form auth-fixed-form"
        :class="{ 'register-mode': isRegisterMode }"
        novalidate
        @submit.prevent="submitAuth"
      >
        <label class="field-label auth-field auth-row-account">
          <span>{{ isRegisterMode ? '账号' : '账号/邮箱' }}</span>
          <input
            v-model.trim="form.username"
            type="text"
            autocomplete="username"
            :placeholder="isRegisterMode ? '请输入账号' : '请输入账号或邮箱'"
            required
          />
        </label>

        <label v-if="isRegisterMode" class="field-label auth-field auth-row-name">
          <span>昵称</span>
          <input v-model.trim="form.displayName" type="text" autocomplete="name" placeholder="请输入昵称" required />
        </label>

        <label v-if="isRegisterMode" class="field-label auth-field auth-row-email">
          <span>邮箱</span>
          <input v-model.trim="form.email" type="email" autocomplete="email" placeholder="请输入邮箱地址" required />
          <span v-if="form.email && !emailPattern.test(form.email)" class="auth-field-hint">邮箱格式不正确</span>
        </label>

        <label v-if="isRegisterMode" class="field-label auth-field auth-row-email-code">
          <span>邮箱验证码</span>
          <div class="auth-email-code-stack">
            <input
              v-model.trim="form.emailCode"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              placeholder="请输入验证码"
              required
            />
            <button
              type="button"
              class="auth-send-code-button"
              :disabled="emailCodeSending || emailCodeCountdown > 0 || !form.email || !emailPattern.test(form.email)"
              @click="sendEmailCode"
            >
              {{ emailCodeButtonText }}
            </button>
          </div>
        </label>

        <label class="field-label auth-field auth-row-password">
          <span>密码</span>
          <div class="auth-password-stack">
            <div class="password-field">
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                :autocomplete="isRegisterMode ? 'new-password' : 'current-password'"
                placeholder="请输入密码"
                required
              />
              <button
                class="text-button auth-eye-button"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" class="auth-eye-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M2 12s3.7-7 10-7 10 7 10 7-3.7 7-10 7S2 12 2 12Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else class="auth-eye-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 3l18 18" />
                  <path d="M10.7 5.1A10.9 10.9 0 0 1 12 5c5 0 8.7 4.1 10 7a12.2 12.2 0 0 1-3.2 4.4" />
                  <path d="M6.5 6.5A12.6 12.6 0 0 0 2 12c1.3 2.9 5 7 10 7 1.5 0 2.8-.3 4-.9" />
                  <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
                  <path d="M14.1 9.9A3 3 0 0 0 12 9" />
                </svg>
              </button>
            </div>

            <div v-if="isRegisterMode" class="password-field">
              <input
                v-model="form.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="请再次输入密码"
                required
              />
              <button
                class="text-button auth-eye-button"
                type="button"
                :aria-label="showConfirmPassword ? '隐藏密码' : '显示密码'"
                @click="showConfirmPassword = !showConfirmPassword"
              >
                <svg v-if="showConfirmPassword" class="auth-eye-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M2 12s3.7-7 10-7 10 7 10 7-3.7 7-10 7S2 12 2 12Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else class="auth-eye-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 3l18 18" />
                  <path d="M10.7 5.1A10.9 10.9 0 0 1 12 5c5 0 8.7 4.1 10 7a12.2 12.2 0 0 1-3.2 4.4" />
                  <path d="M6.5 6.5A12.6 12.6 0 0 0 2 12c1.3 2.9 5 7 10 7 1.5 0 2.8-.3 4-.9" />
                  <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
                  <path d="M14.1 9.9A3 3 0 0 0 12 9" />
                </svg>
              </button>
            </div>
          </div>
        </label>

        <div v-if="isRegisterMode" class="auth-password-strength" :class="passwordStrength.level">
          <div class="strength-bar-track">
            <div class="strength-bar-fill"></div>
          </div>
          <span class="strength-label">{{ passwordStrength.label }}</span>
        </div>

        <label v-if="captchaRequired" class="field-label auth-field">
          <span>验证码：{{ captchaQuestion }}</span>
          <input
            v-model.trim="form.captchaAnswer"
            type="text"
            inputmode="numeric"
            autocomplete="off"
            placeholder="请输入计算结果"
            required
          />
        </label>

        <label v-if="isRegisterMode" class="auth-agreement">
          <input v-model="form.acceptTerms" type="checkbox" />
          <span>我已阅读并同意用户协议与隐私政策</span>
        </label>

        <div class="auth-message-slot" :class="{ 'has-message': authMessage }">
          <p v-if="authMessage" class="auth-message" :class="{ error: authError }">
            {{ authMessage }}
          </p>
        </div>

        <button class="primary-button auth-submit" type="submit" :disabled="authLoading">
          {{ submitButtonText }}
        </button>

        <p v-if="!isRegisterMode" class="auth-login-hint">
          {{ portalMode === 'admin' ? '将跳转到后台管理系统，并使用管理员系统登录' : '首次登录将自动创建账号' }}
        </p>
      </form>
    </section>
  </main>
</template>

<script setup>
import { computed, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getLoginCaptcha, loginUser, registerUser, sendRegisterEmailCode } from '../services/api.js'
import { setAuthSession } from '../stores/auth.js'

function getAdminHomeUrl() {
  if (import.meta.env.DEV) return 'http://localhost:9527/dashboard'
  return `${window.location.origin}/admin/dashboard`
}
const DEFAULT_USER_AVATAR = '/userlogo.png'

const router = useRouter()
const mode = ref('login')
const portalMode = ref('user')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const authLoading = ref(false)
const authMessage = ref('')
const authError = ref(false)
const emailCodeSending = ref(false)
const emailCodeCountdown = ref(0)
const captchaRequired = ref(false)
const captchaId = ref('')
const captchaQuestion = ref('')
let emailCodeTimer = null

const form = reactive({
  username: '',
  email: '',
  emailCode: '',
  displayName: '',
  password: '',
  confirmPassword: '',
  captchaAnswer: '',
  acceptTerms: false,
})

const emailPattern = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/
const isRegisterMode = computed(() => mode.value === 'register')

const passwordStrength = computed(() => {
  const password = form.password || ''
  let score = 0
  if (password.length >= 8) score += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password)) score += 1
  if (score >= 4) return { label: '强', level: 'strong' }
  if (score >= 2) return { label: '中', level: 'medium' }
  return { label: '弱', level: 'weak' }
})

const emailCodeButtonText = computed(() => {
  if (emailCodeCountdown.value > 0) return `${emailCodeCountdown.value}s 后重发`
  return emailCodeSending.value ? '发送中...' : '发送验证码'
})

const submitButtonText = computed(() => {
  if (authLoading.value) return '处理中...'
  if (isRegisterMode.value) return '注册并进入'
  return portalMode.value === 'admin' ? '进入管理员端' : '登录'
})

function resetAuthFeedback() {
  authMessage.value = ''
  authError.value = false
  captchaRequired.value = false
  captchaId.value = ''
  captchaQuestion.value = ''
  form.captchaAnswer = ''
}

function setPortal(nextPortal) {
  portalMode.value = nextPortal
  resetAuthFeedback()
  if (nextPortal === 'admin' && isRegisterMode.value) {
    setMode('login')
  }
}

function setMode(nextMode) {
  mode.value = nextMode
  resetAuthFeedback()
  form.emailCode = ''
  emailCodeSending.value = false
  emailCodeCountdown.value = 0
  if (emailCodeTimer) {
    clearInterval(emailCodeTimer)
    emailCodeTimer = null
  }
  showPassword.value = false
  showConfirmPassword.value = false
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

function persistUser(user) {
  setAuthSession({ ...user, avatarUrl: user.avatarUrl || DEFAULT_USER_AVATAR })
}

function validateAuthForm() {
  const username = form.username.trim()
  if (!isRegisterMode.value && username.includes('@')) {
    if (!emailPattern.test(username)) return '请输入正确的邮箱地址'
  } else if (!/^[A-Za-z0-9_@.\-\u4e00-\u9fa5]{3,32}$/.test(username)) {
    return '账号长度需为 3-32 位，只能包含中文、字母、数字、下划线、点、@ 或短横线'
  }
  if (!form.password || form.password.length < 8) return '密码至少 8 位'
  if (isRegisterMode.value && form.password !== form.confirmPassword) return '两次输入的密码不一致'
  if (isRegisterMode.value && passwordStrength.value.level === 'weak') return '密码强度过弱，请增加数字、大小写字母或符号'
  if (isRegisterMode.value && !form.email) return '请输入邮箱地址'
  if (isRegisterMode.value && !emailPattern.test(form.email.trim())) return '请输入正确的邮箱地址'
  if (isRegisterMode.value && !form.emailCode) return '请输入邮箱验证码'
  if (isRegisterMode.value && !form.acceptTerms) return '注册前请先同意用户协议与隐私政策'
  if (captchaRequired.value && !form.captchaAnswer) return '请输入验证码'
  return ''
}

async function sendEmailCode() {
  authMessage.value = ''
  authError.value = false
  const email = form.email.trim()
  if (!emailPattern.test(email)) {
    authMessage.value = '请输入正确的邮箱地址'
    authError.value = true
    return
  }
  emailCodeSending.value = true
  try {
    const result = await sendRegisterEmailCode({ email })
    authMessage.value = result.msg || '验证码已发送，请查收邮箱'
    authError.value = false
    startEmailCodeCountdown(60)
  } catch (error) {
    const data = error.response?.data || {}
    authMessage.value = data.msg || data.message || '验证码发送失败，请稍后再试'
    authError.value = true
  } finally {
    emailCodeSending.value = false
  }
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
  form.captchaAnswer = ''
}

async function submitAuth() {
  authMessage.value = ''
  authError.value = false

  const validationMessage = validateAuthForm()
  if (validationMessage) {
    authMessage.value = validationMessage
    authError.value = true
    return
  }

  authLoading.value = true
  try {
    const payload = {
      username: form.username.trim(),
      email: form.email.trim(),
      emailCode: form.emailCode.trim(),
      password: form.password,
      displayName: form.displayName.trim(),
      captchaId: captchaId.value,
      captchaAnswer: form.captchaAnswer,
    }
    const user = isRegisterMode.value ? await registerUser(payload) : await loginUser(payload)
    persistUser(user)
    if (portalMode.value === 'admin' && !isRegisterMode.value) {
      if (user.role !== 'admin') {
        authMessage.value = '当前账号不是管理员，请切换管理员账号登录'
        authError.value = true
        return
      }
      localStorage.setItem('appMode', 'admin')
      localStorage.setItem('SOY_token', JSON.stringify(user.token))
      localStorage.setItem('SOY_refreshToken', JSON.stringify(user.token))
      localStorage.setItem('SOY_lastLoginUserId', JSON.stringify(String(user.id)))
      authMessage.value = '正在进入管理员端...'
      window.location.href = getAdminHomeUrl()
      return
    }
    localStorage.setItem('appMode', 'user')
    authMessage.value = isRegisterMode.value ? '注册成功，正在进入系统...' : '登录成功，正在进入系统...'
    await router.push('/learning-profile')
  } catch (error) {
    const data = error.response?.data || {}
    if (data.captchaRequired) await refreshCaptcha(data)
    authMessage.value = data.msg || data.message || '认证失败，请稍后再试'
    authError.value = true
  } finally {
    authLoading.value = false
  }
}
</script>
