<template>
  <form class="space-y-5" novalidate @submit.prevent="$emit('submit')">
    <label class="block">
      <span class="mb-2 block text-sm font-semibold text-slate-700">账号/邮箱</span>
      <span class="relative block">
        <UserRound class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" :size="21" />
        <input
          v-model.trim="form.username"
          class="h-14 w-full rounded-2xl border border-slate-200/90 bg-white/72 pl-12 pr-4 text-base text-slate-800 outline-none transition duration-300 placeholder:text-slate-400 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-100/90"
          type="text"
          autocomplete="username"
          placeholder="请输入账号或邮箱"
          required
        />
      </span>
    </label>

    <label class="block">
      <span class="mb-2 block text-sm font-semibold text-slate-700">密码</span>
      <span class="password-field relative block">
        <LockKeyhole class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" :size="21" />
        <input
          v-model="form.password"
          class="h-14 w-full rounded-2xl border border-slate-200/90 bg-white/72 pl-12 pr-14 text-base text-slate-800 outline-none transition duration-300 placeholder:text-slate-400 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-100/90"
          :type="showPassword ? 'text' : 'password'"
          autocomplete="current-password"
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

    <label v-if="captchaRequired" class="block">
      <span class="mb-2 block text-sm font-semibold text-slate-700">验证码：{{ captchaQuestion }}</span>
      <input
        v-model.trim="form.captchaAnswer"
        class="h-14 w-full rounded-2xl border border-slate-200/90 bg-white/72 px-4 text-base text-slate-800 outline-none transition duration-300 placeholder:text-slate-400 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-100/90"
        type="text"
        inputmode="numeric"
        autocomplete="off"
        placeholder="请输入计算结果"
        required
      />
    </label>

    <div class="min-h-[24px]">
      <p
        v-if="message"
        class="text-sm"
        :class="error ? 'text-rose-500' : 'text-brand-600'"
      >
        {{ message }}
      </p>
    </div>

    <button
      type="submit"
      class="auth-primary-action group flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-brand-500 to-brand-600 text-lg font-semibold text-white shadow-[0_14px_30px_rgba(16,185,129,0.28)] transition duration-300 hover:-translate-y-0.5 hover:shadow-glow disabled:translate-y-0 disabled:opacity-70"
      :disabled="loading"
    >
      <Loader2 v-if="loading" class="animate-spin" :size="21" />
      <span>登录</span>
      <ArrowRight v-if="!loading" class="transition duration-300 group-hover:translate-x-0.5" :size="20" />
    </button>

    <p class="text-center text-sm text-slate-400">没有账号请先切换到注册</p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { ArrowRight, Eye, EyeOff, Loader2, LockKeyhole, UserRound } from 'lucide-vue-next'

defineProps({
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
  captchaRequired: {
    type: Boolean,
    default: false,
  },
  captchaQuestion: {
    type: String,
    default: '',
  },
})

defineEmits(['submit'])

const showPassword = ref(false)
</script>

<style scoped>
.password-field .password-visibility-toggle {
  position: relative;
  z-index: 1;
  grid-area: 1 / 1;
  align-self: center;
  justify-self: end;
  display: grid;
  width: 32px;
  height: 32px;
  margin-right: 10px;
  place-items: center;
  border: 0 !important;
  border-radius: 0 !important;
  outline: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #64748b;
  cursor: pointer;
  transform: none !important;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.password-field {
  display: grid !important;
}

.password-field > :is(input, svg) {
  grid-area: 1 / 1;
}

.password-field .password-visibility-toggle:hover,
.password-field .password-visibility-toggle:focus-visible {
  border: 0 !important;
  outline: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #047857;
}
</style>
