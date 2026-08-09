<template>
  <div v-if="loading" class="state-block" role="status"><span class="spinner"></span><strong>{{ loadingText }}</strong></div>
  <div v-else-if="error" class="state-block error" role="alert"><CircleAlert :size="24" /><strong>{{ error }}</strong><button type="button" @click="$emit('retry')"><RotateCcw :size="16" />重试</button></div>
  <div v-else-if="empty" class="state-block"><Inbox :size="26" /><strong>{{ emptyText }}</strong><slot name="action" /></div>
  <slot v-else />
</template>
<script setup>
import { CircleAlert, Inbox, RotateCcw } from 'lucide-vue-next'
defineProps({ loading: Boolean, error: String, empty: Boolean, loadingText: { type: String, default: '正在加载' }, emptyText: { type: String, default: '暂无数据' } })
defineEmits(['retry'])
</script>
