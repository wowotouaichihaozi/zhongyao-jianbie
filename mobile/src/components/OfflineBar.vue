<template><div v-if="!online" class="offline-bar" role="status"><WifiOff :size="15" /> 网络已断开，暂时无法同步学习数据</div></template>
<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { WifiOff } from 'lucide-vue-next'
const online = ref(navigator.onLine)
const update = () => { online.value = navigator.onLine }
onMounted(() => { window.addEventListener('online', update); window.addEventListener('offline', update) })
onBeforeUnmount(() => { window.removeEventListener('online', update); window.removeEventListener('offline', update) })
</script>
