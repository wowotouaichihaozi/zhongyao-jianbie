<template>
  <div class="grid grid-cols-2 gap-2" role="radiogroup" aria-label="选择登录角色">
    <button
      v-for="option in roles"
      :key="option.value"
      type="button"
      class="auth-role-option group relative flex min-h-[54px] items-center gap-2 overflow-hidden rounded-2xl border px-3 text-left transition duration-300 hover:-translate-y-0.5 hover:shadow-lg sm:min-h-[58px] sm:gap-2.5 sm:px-4"
      :class="modelValue === option.value
        ? 'auth-role-option-active border-brand-400/70 bg-gradient-to-br from-brand-50/95 to-white shadow-[0_18px_38px_rgba(16,185,129,0.16)]'
        : 'border-slate-200/80 bg-white/58 hover:border-brand-200 hover:bg-white/82'"
      role="radio"
      :aria-checked="modelValue === option.value"
      @click="$emit('update:modelValue', option.value)"
    >
      <span
        class="grid h-8 w-8 shrink-0 place-items-center rounded-xl transition duration-300 sm:h-9 sm:w-9"
        :class="modelValue === option.value
          ? 'bg-white text-brand-500 shadow-[0_12px_28px_rgba(16,185,129,0.18)]'
          : 'bg-slate-100 text-slate-400 group-hover:bg-brand-50 group-hover:text-brand-500'"
      >
        <component :is="option.icon" :size="20" stroke-width="2.25" />
      </span>
      <span class="min-w-0">
        <span
          class="block whitespace-nowrap text-sm font-semibold tracking-[0] sm:text-base"
          :class="modelValue === option.value ? 'text-brand-700' : 'text-slate-700'"
        >
          {{ option.label }}
        </span>
        <span class="mt-0.5 block whitespace-nowrap text-xs text-slate-500">{{ option.caption }}</span>
      </span>
      <span
        v-if="modelValue === option.value"
        class="absolute inset-x-5 bottom-0 h-0.5 rounded-full bg-gradient-to-r from-brand-400 to-brand-600"
      ></span>
    </button>
  </div>
</template>

<script setup>
import { ShieldCheck, UserRound } from 'lucide-vue-next'

defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

defineEmits(['update:modelValue'])

const roles = [
  {
    value: 'user',
    label: '用户端',
    caption: '学习平台',
    icon: UserRound,
  },
  {
    value: 'admin',
    label: '管理员端',
    caption: '后台管理',
    icon: ShieldCheck,
  },
]
</script>
