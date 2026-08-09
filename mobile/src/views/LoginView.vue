<template>
  <main class="login-page">
    <div class="login-visual" aria-hidden="true">
      <img :src="`${baseUrl}login-chip-v1.webp`" alt="" />
    </div>

    <div class="login-layout">
      <header class="brand-lockup">
        <img :src="`${baseUrl}logo.png`" alt="嵌智学航" />
        <div>
          <strong>嵌智学航</strong>
          <span>智能学习导航</span>
        </div>
      </header>

      <form class="login-form" @submit.prevent="submit">
        <section class="login-intro" aria-labelledby="login-title">
          <span>PERSONAL LEARNING</span>
          <h1 id="login-title">继续你的专属学习路径</h1>
          <p>画像驱动路径，学习证据持续更新。</p>
        </section>

        <div class="login-form-head">
          <div>
            <small>欢迎回来</small>
            <strong>登录学习空间</strong>
          </div>
          <span class="secure-mark"><ShieldCheck :size="17" aria-hidden="true" />安全连接</span>
        </div>

        <label class="field">
          <span>账号</span>
          <input
            v-model.trim="form.username"
            autocomplete="username"
            placeholder="用户名或邮箱"
            required
          />
        </label>
        <label class="field">
          <span>密码</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            placeholder="输入密码"
            minlength="8"
            required
          />
        </label>
        <label v-if="captcha.question" class="field">
          <span>验证码：{{ captcha.question }}</span>
          <input v-model.trim="form.captchaAnswer" inputmode="numeric" required />
        </label>

        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="primary-btn full-btn" :disabled="loading">
          <span v-if="loading" class="spinner light"></span>
          <LogIn v-else :size="18" aria-hidden="true" />
          {{ loading ? '正在登录' : '进入学习空间' }}
        </button>
        <p class="session-note">与网页版共用账号和学习数据</p>
      </form>
    </div>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LogIn, ShieldCheck } from 'lucide-vue-next'
import { getCaptcha, login } from '../services/api.js'
import { setAuthSession } from '../stores/auth.js'

const router = useRouter()
const route = useRoute()
const baseUrl = import.meta.env.BASE_URL
const form = reactive({ username: '', password: '', captchaAnswer: '' })
const captcha = reactive({ captchaId: '', question: '' })
const loading = ref(false)
const error = ref('')

async function loadCaptcha(details = {}) {
  const data = details.captchaId ? details : await getCaptcha()
  captcha.captchaId = data.captchaId || ''
  captcha.question = data.question || ''
  form.captchaAnswer = ''
}

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const user = await login({ ...form, captchaId: captcha.captchaId })
    setAuthSession(user)
    await router.replace(String(route.query.redirect || '/home'))
  } catch (err) {
    error.value = err.message
    if (err.details?.captchaRequired || err.details?.captchaId) await loadCaptcha(err.details)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100dvh;
  overflow-x: hidden;
  overflow-y: auto;
  background: #0b2526;
}

.login-visual {
  position: fixed;
  inset: 0;
  height: 100dvh;
  overflow: hidden;
  background: #0b2526;
}

.login-visual::after {
  content: "";
  position: absolute;
  inset: 0;
  background: rgba(4, 24, 26, .28);
}

.login-visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 68% center;
}

.login-layout {
  position: relative;
  z-index: 1;
  width: min(520px, 100%);
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  margin: 0 auto;
  padding: calc(18px + env(safe-area-inset-top)) 16px calc(22px + env(safe-area-inset-bottom));
}

.brand-lockup {
  position: absolute;
  top: calc(18px + env(safe-area-inset-top));
  left: 16px;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.brand-lockup img {
  width: 42px;
  height: 34px;
  object-fit: contain;
  filter: drop-shadow(0 2px 5px rgba(24, 55, 41, .12));
}

.brand-lockup strong,
.brand-lockup span {
  display: block;
  letter-spacing: 0;
}

.brand-lockup strong {
  color: #ffffff;
  font-size: 13px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, .3);
}

.brand-lockup span {
  margin-top: 1px;
  color: rgba(255, 255, 255, .78);
  font-size: 8px;
}

.login-intro {
  margin: 0;
  padding: 0 0 12px;
  border-bottom: 1px solid rgba(67, 100, 87, .2);
}

.login-intro > span {
  color: #176f4b;
  font-size: 9px;
  font-weight: 850;
}

.login-intro h1 {
  margin: 5px 0 0;
  color: #17231e;
  font-size: 24px;
  line-height: 1.28;
  text-shadow: none;
}

.login-intro p {
  margin: 6px 0 0;
  color: #5d6d65;
  font-size: 11px;
  line-height: 1.55;
}

.login-form {
  display: grid;
  gap: 12px;
  margin: auto 0;
  padding: 17px 16px 13px;
  border: 1px solid rgba(255, 255, 255, .62);
  border-radius: 8px;
  background: rgba(247, 252, 250, .68);
  box-shadow: 0 20px 50px rgba(2, 20, 22, .28);
  backdrop-filter: blur(22px) saturate(135%);
  -webkit-backdrop-filter: blur(22px) saturate(135%);
}

.login-form-head {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 11px;
  border-bottom: 1px solid rgba(67, 100, 87, .2);
}

.login-form-head strong,
.login-form-head small {
  display: block;
}

.login-form-head small {
  color: #718179;
  font-size: 9px;
}

.login-form-head strong {
  margin-top: 2px;
  color: #20342b;
  font-size: 15px;
}

.secure-mark {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 7px;
  border-radius: 4px;
  background: #edf5f1;
  color: #176f4b;
  font-size: 9px;
  font-weight: 750;
}

.login-form .field {
  gap: 5px;
}

.login-form .field input {
  min-height: 48px;
  border-color: rgba(74, 108, 94, .28);
  background: rgba(255, 255, 255, .68);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .7);
  backdrop-filter: blur(8px);
}

.login-form .field input:focus {
  border-color: #176f4b;
  background: rgba(255, 255, 255, .88);
  box-shadow: 0 0 0 3px rgba(23, 111, 75, .13);
}

.login-form .primary-btn {
  min-height: 48px;
}

.form-error {
  margin: 0;
  padding: 9px 11px;
  border-left: 3px solid #b04c3b;
  background: #fff0ec;
  color: #a04435;
  font-size: 11px;
}

.session-note {
  margin: -3px 0 0;
  color: #7b8982;
  font-size: 9px;
  text-align: center;
}

.spinner.light {
  border-color: rgba(255, 255, 255, .45);
  border-top-color: #fff;
}

@media (max-width: 360px) {
  .login-layout { padding-right: 13px; padding-left: 13px; }
  .brand-lockup { left: 13px; }
  .login-intro h1 { font-size: 22px; }
  .login-form { padding: 15px 14px 12px; }
}

@media (min-width: 700px) and (max-width: 899px) {
  .login-layout { width: min(560px, 100%); }
}

@media (min-width: 900px) {
  .login-visual img { object-position: 68% center; }
  .login-layout {
    width: min(520px, 100%);
    padding: 30px 32px;
  }
  .login-intro {
    padding-top: 0;
  }
  .login-intro h1 { font-size: 32px; }
  .login-intro p { font-size: 13px; }
  .login-form {
    margin: auto 0;
    padding: 25px;
  }
}

@media (orientation: landscape) and (max-height: 520px) and (max-width: 899px) {
  .login-page { overflow: auto; }
  .login-visual img { object-position: 68% center; }
  .login-layout { width: 55%; min-width: 430px; margin: 0 0 0 auto; padding: 14px 20px; }
  .brand-lockup { display: none; }
  .login-intro { padding-top: 0; }
  .login-intro h1 { font-size: 22px; }
  .login-intro p { margin-top: 3px; }
  .login-form { gap: 8px; margin-top: 9px; padding: 13px 15px 10px; }
  .login-form-head { min-height: 34px; padding-bottom: 7px; }
  .login-form .field { grid-template-columns: 54px minmax(0, 1fr); align-items: center; }
  .login-form .field input { min-height: 44px; }
  .login-form .primary-btn { min-height: 44px; }
}
</style>
