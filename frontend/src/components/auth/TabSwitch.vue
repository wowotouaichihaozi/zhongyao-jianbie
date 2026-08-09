<template>
  <div class="relative border-b border-slate-200/80" role="tablist" aria-label="认证方式">
    <div
      class="absolute bottom-[-1px] h-[3px] w-1/2 rounded-full bg-gradient-to-r from-brand-400 to-brand-600 transition-transform duration-300 ease-out"
      :style="{ transform: modelValue === 'register' ? 'translateX(100%)' : 'translateX(0)' }"
      aria-hidden="true"
    ></div>
    <div class="grid grid-cols-2">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="auth-tab-action relative py-2.5 text-base font-semibold transition duration-300"
        :class="modelValue === tab.value ? 'auth-tab-action-active text-brand-600' : 'text-slate-400 hover:text-slate-600'"
        role="tab"
        :aria-selected="modelValue === tab.value"
        @click="$emit('update:modelValue', tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

defineEmits(['update:modelValue'])

const tabs = [
  { value: 'login', label: '登录' },
  { value: 'register', label: '注册' },
]
</script>
