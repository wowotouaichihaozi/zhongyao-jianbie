<template>
  <nav class="bottom-nav" aria-label="主导航">
    <RouterLink v-for="item in items" :key="item.to" :to="item.to" :class="{ active: isActive(item) }">
      <component :is="item.icon" :size="22" stroke-width="2.1" />
      <span>{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

<script setup>
import { Bot, Compass, Home, Library, UserRound } from 'lucide-vue-next'
import { RouterLink, useRoute } from 'vue-router'
const route = useRoute()
const items = [
  { to: '/home', label: '首页', icon: Home },
  { to: '/path', label: '路径', icon: Compass },
  { to: '/resources', label: '资源', icon: Library },
  { to: '/tutor', label: '辅导', icon: Bot },
  { to: '/me', label: '我的', icon: UserRound },
]
function isActive(item) { return route.path === item.to || route.path.startsWith(`${item.to}/`) }
</script>
