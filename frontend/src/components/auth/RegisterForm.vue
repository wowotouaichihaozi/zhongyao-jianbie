<template>
  <form class="space-y-1.5" novalidate @submit.prevent="$emit('submit')">
    <div class="grid gap-2 sm:grid-cols-2">
      <label class="block">
        <span class="block text-xs font-semibold text-slate-700">账号</span>
        <span class="relative block">
          <UserRound class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" :size="18" />
          <input
            v-model.trim="form.username"
            class="auth-input pl-10"
            type="text"
            autocomplete="username"
            placeholder="请输入账号"
            required
          />
        </span>
      </label>

      <label class="block">
        <span class="block text-xs font-semibold text-slate-700">昵称</span>
        <span class="relative block">
          <Sparkles class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" :size="18" />
          <input
            v-model.trim="form.displayName"
            class="auth-input pl-10"
            type="text"
            autocomplete="name"
            placeholder="请输入昵称"
            required
          />
        </span>
      </label>
    </div>

    <label class="block">
      <span class="block text-xs font-semibold text-slate-700">邮箱</span>
      <span class="relative block">
        <Mail class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" :size="18" />
        <input
          v-model.trim="form.email"
          class="auth-input pl-10"
          type="email"
          autocomplete="email"
          placeholder="请输入邮箱地址"
          required
        />
      </span>
    </label>

    <label class="block">
      <span class="block text-xs font-semibold text-slate-700">邮箱验证码</span>
      <span class="grid gap-2 sm:grid-cols-[1fr_auto]">
        <input
          v-model.trim="form.emailCode"
          class="auth-input px-3.5"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          placeholder="请输入验证码"
          required
        />
        <button
          type="button"
          class="auth-code-action h-10 rounded-2xl border border-brand-300/80 bg-white/80 px-4 text-sm font-semibold text-brand-600 transition duration-300 hover:-translate-y-0.5 hover:bg-brand-50 hover:shadow-[0_12px_24px_rgba(16,185,129,0.14)] disabled:translate-y-0 disabled:border-slate-200 disabled:text-slate-400 disabled:shadow-none"
          :disabled="!canSendCode"
          @click="$emit('send-email-code')"
        >
          {{ codeButtonText }}
        </button>
      </span>
    </label>

    <label class="block">
      <span class="block text-xs font-semibold text-slate-700">密码</span>
      <span class="password-field relative block">
        <LockKeyhole class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" :size="18" />
        <input
          v-model="form.password"
          class="auth-input pl-10 pr-12"
          :type="showPassword ? 'text' : 'password'"
          autocomplete="new-password"
          placeholder="请输入密码"
          required
        />
        <span
          class="password-visibility-toggle"
          role="button"
          tabindex="0"
          :aria-label="showPassword ? '隐藏密码' : '显示密码'"
          @click="showPassword = !showPassword"
          @keydown.enter.prevent="showPassword = !showPassword"
          @keydown.space.prevent="showPassword = !showPassword"
        >
          <Eye v-if="showPassword" :size="18" :stroke-width="2" />
          <EyeOff v-else :size="18" :stroke-width="2" />
        </span>
      </span>
    </label>

    <label class="block">
      <span class="block text-xs font-semibold text-slate-700">确认密码</span>
      <span class="password-field relative block">
        <LockKeyhole class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" :size="18" />
        <input
          v-model="form.confirmPassword"
          class="auth-input pl-10 pr-12"
          :type="showConfirmPassword ? 'text' : 'password'"
          autocomplete="new-password"
          placeholder="请再次输入密码"
          required
        />
        <span
          class="password-visibility-toggle"
          role="button"
          tabindex="0"
          :aria-label="showConfirmPassword ? '隐藏密码' : '显示密码'"
          @click="showConfirmPassword = !showConfirmPassword"
          @keydown.enter.prevent="showConfirmPassword = !showConfirmPassword"
          @keydown.space.prevent="showConfirmPassword = !showConfirmPassword"
        >
          <Eye v-if="showConfirmPassword" :size="18" :stroke-width="2" />
          <EyeOff v-else :size="18" :stroke-width="2" />
        </span>
      </span>
    </label>

    <div class="flex items-center gap-2.5">
      <div class="grid flex-1 grid-cols-3 gap-1.5" aria-hidden="true">
        <span
          v-for="index in 3"
          :key="index"
        class="h-1 rounded-full transition duration-300"
          :class="index <= strengthLevel ? strengthColor : 'bg-slate-200'"
        ></span>
      </div>
      <span class="w-7 text-right text-xs font-semibold" :class="strengthTextColor">
        {{ passwordStrength.label }}
      </span>
    </div>

    <label class="flex items-start gap-2 text-xs leading-tight text-slate-500">
      <input
        v-model="form.acceptTerms"
        class="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-500 accent-brand-500"
        type="checkbox"
      />
      <span>我已阅读并同意 <a class="font-semibold text-brand-600" href="#">用户协议</a> 与 <a class="font-semibold text-brand-600" href="#">隐私政策</a></span>
    </label>

    <div class="min-h-[14px]">
      <p
        v-if="message"
        class="text-xs"
        :class="error ? 'text-rose-500' : 'text-brand-600'"
      >
        {{ message }}
      </p>
    </div>

    <button
      type="submit"
      class="auth-primary-action group flex h-10 w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-brand-500 to-brand-600 text-base font-semibold text-white shadow-[0_14px_30px_rgba(16,185,129,0.28)] transition duration-300 hover:-translate-y-0.5 hover:shadow-glow disabled:translate-y-0 disabled:opacity-70"
      :disabled="loading"
    >
      <Loader2 v-if="loading" class="animate-spin" :size="19" />
      <span>注册并进入</span>
      <ArrowRight v-if="!loading" class="transition duration-300 group-hover:translate-x-0.5" :size="18" />
    </button>
  </form>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ArrowRight, Eye, EyeOff, Loader2, LockKeyhole, Mail, Sparkles, UserRound } from 'lucide-vue-next'

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  message: {
    type: String,
    default: '',
  },
  error: {
    type: Boolean,
    default: false,
  },
  emailValid: {
    type: Boolean,
    default: false,
  },
  emailCodeSending: {
    type: Boolean,
    default: false,
  },
  emailCodeCountdown: {
    type: Number,
    default: 0,
  },
  passwordStrength: {
    type: Object,
    required: true,
  },
})

defineEmits(['submit', 'send-email-code'])

const showPassword = ref(false)
const showConfirmPassword = ref(false)

const canSendCode = computed(() => (
  props.emailValid
  && !props.emailCodeSending
  && props.emailCodeCountdown <= 0
))

const codeButtonText = computed(() => {
  if (props.emailCodeCountdown > 0) return `${props.emailCodeCountdown}s 后重发`
  return props.emailCodeSending ? '发送中...' : '发送验证码'
})

const strengthLevel = computed(() => {
  if (props.passwordStrength.level === 'strong') return 3
  if (props.passwordStrength.level === 'medium') return 2
  return 1
})

const strengthColor = computed(() => {
  if (props.passwordStrength.level === 'strong') return 'bg-brand-500'
  if (props.passwordStrength.level === 'medium') return 'bg-amber-400'
  return 'bg-rose-400'
})

const strengthTextColor = computed(() => {
  if (props.passwordStrength.level === 'strong') return 'text-brand-600'
  if (props.passwordStrength.level === 'medium') return 'text-amber-500'
  return 'text-rose-500'
})
</script>

<style scoped>
.auth-input {
  height: 2.5rem;
  width: 100%;
  border-radius: 1rem;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.72);
  color: #1e293b;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
}

.auth-input::placeholder {
  color: #94a3b8;
}

.auth-input:focus {
  border-color: #34d399;
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(209, 250, 229, 0.9);
}

.password-field .password-visibility-toggle {
  position: absolute;
  z-index: 1;
  right: 10px;
  top: 50%;
  display: grid;
  width: 32px;
  height: 32px;
  transform: translateY(-50%);
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.password-field .password-visibility-toggle:hover,
.password-field .password-visibility-toggle:focus-visible {
  background: #ecfdf5;
  color: #047857;
  outline: none;
}

.password-field .password-visibility-toggle:focus-visible {
  box-shadow: 0 0 0 2px #a7f3d0;
}
</style>
