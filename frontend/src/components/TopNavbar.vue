<template>
  <header class="topnavbar">
    <RouterLink class="brand" to="/login" aria-label="返回中药鉴别登录页">
      <img src="/qihuang-zhijing-mark-512.png" alt="" />
      <span class="brand-copy"><strong>中药鉴别</strong><small>中医智慧学习平台</small></span>
    </RouterLink>

    <nav class="nav-links" aria-label="主功能导航">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :class="{ active: item.active?.() }"
      >
        <img v-if="item.logo" class="nav-item-logo" :src="item.logo" alt="" aria-hidden="true" />
        <component v-else :is="item.icon" :size="18" :stroke-width="2" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <nav class="mobile-bottom-nav" aria-label="移动端主导航">
      <RouterLink
        v-for="item in mobileNavItems"
        :key="item.to"
        :to="item.to"
        :class="{ active: item.active?.() }"
      >
        <img v-if="item.logo" class="nav-item-logo" :src="item.logo" alt="" aria-hidden="true" />
        <component v-else :is="item.icon" :size="21" :stroke-width="2.2" />
        <span>{{ item.mobileLabel || item.label }}</span>
      </RouterLink>
    </nav>

    <div class="nav-right">
      <button class="icon-button notification-button" type="button" aria-label="通知">
        <Bell :size="19" :stroke-width="2" />
      </button>
      <RouterLink class="user-avatar-link" to="/user-profile" aria-label="用户头像">
        <img :src="userAvatar" alt="用户头像" class="user-avatar" />
      </RouterLink>
      <button class="logout-button" type="button" @click="logout">
        <LogOut :size="18" :stroke-width="2" />
        <span>退出</span>
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import {
  Bell,
  ChartNoAxesCombined,
  Gauge,
  FlaskConical,
  LogOut,
  Network,
  Orbit,
  Route as RouteIcon,
  ScanSearch,
  Share2,
  TreePine,
  UserRound,
} from 'lucide-vue-next'
import { logoutUser } from '../services/api.js'
import { clearAuthSession, readCurrentUser } from '../stores/auth.js'

const router = useRouter()
const route = useRoute()

const isResourceSection = computed(() => {
  return route.path.startsWith('/personalized-resources') || route.path.startsWith('/resource-detail')
})

const navItems = [
  { to: '/learning-profile', label: '学习画像', mobileLabel: '画像', icon: Network, active: () => route.path.startsWith('/learning-profile') },
  { to: '/learning-path', label: '学习路径', mobileLabel: '路径', icon: RouteIcon, active: () => route.path.startsWith('/learning-path') },
  { to: '/personalized-resources', label: '个性化资源', mobileLabel: '资源', icon: FlaskConical, active: () => isResourceSection.value },
  { to: '/herb-recognition', label: '药材识别', mobileLabel: '识别', icon: ScanSearch, active: () => route.path.startsWith('/herb-recognition') },
  { to: '/knowledge-network', label: '知识网络', mobileLabel: '知识', icon: Share2, active: () => route.path.startsWith('/knowledge-network') },
  { to: '/life-tree', label: '生命树', mobileLabel: '生命树', icon: TreePine, active: () => route.path.startsWith('/life-tree') },
  { to: '/agent-digital-twin', label: '数字孪生', mobileLabel: '孪生', icon: Orbit, active: () => route.path.startsWith('/agent-digital-twin') },
  { to: '/effect-assessment', label: '效果评估', mobileLabel: '评估', icon: Gauge, active: () => route.path.startsWith('/effect-assessment') },
  { to: '/digital-human-interview', label: '学习访谈', mobileLabel: '访谈', icon: ChartNoAxesCombined, active: () => route.path.startsWith('/digital-human-interview') },
]

const mobileNavItems = [
  ...navItems.filter(item => item.to !== '/digital-human-interview'),
  { to: '/user-profile', label: '我的', mobileLabel: '我的', icon: UserRound, active: () => route.path.startsWith('/user-profile') },
]

const DEFAULT_USER_AVATAR = '/userlogo.png'
const userAvatar = ref(DEFAULT_USER_AVATAR)
const userInitial = ref('U')

function normalizeAvatar(avatar) {
  if (!avatar || String(avatar).startsWith('data:image/svg+xml')) return DEFAULT_USER_AVATAR
  return avatar
}

function readUser() {
  try {
    const user = readCurrentUser()
    userAvatar.value = normalizeAvatar(user.avatar || user.avatarUrl)
    userInitial.value = (user.displayName || user.username || 'U').charAt(0)
  } catch {
    userAvatar.value = DEFAULT_USER_AVATAR
    userInitial.value = 'U'
  }
}

onMounted(() => {
  readUser()
  window.addEventListener('current-user-change', readUser)
})

onUnmounted(() => {
  window.removeEventListener('current-user-change', readUser)
})

async function logout() {
  try {
    await logoutUser()
  } catch {
    // session may already be expired
  }
  clearAuthSession()
  await router.push('/login')
}
</script>

<style scoped>
.topnavbar {
  position: relative;
  z-index: 100;
  height: 72px;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 240px;
  align-items: center;
  border-bottom: 1px solid #e5e7e7;
  background: #ffffff;
  box-shadow: none;
}

.brand {
  width: 240px;
  height: 72px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding-left: 24px;
  box-sizing: border-box;
  text-decoration: none;
}

.brand img {
  width: 46px;
  height: 46px;
  object-fit: contain;
  filter: none;
  opacity: 1;
}

.brand-copy {
  display: grid;
  gap: 2px;
  color: #123d2d;
  line-height: 1.1;
}

.brand-copy strong { font-size: 18px; }
.brand-copy small { color: #8d4b3d; font-size: 10px; font-weight: 650; }

.nav-links {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-links::-webkit-scrollbar {
  display: none;
}

.nav-links a {
  position: relative;
  height: 72px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  background: transparent;
  color: #697171;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition: color 0.2s ease;
}

.nav-links a:hover,
.nav-links a.active {
  color: #111313;
}

.nav-links a:nth-child(1) svg,
.mobile-bottom-nav a:nth-child(1) svg {
  color: #0f8f8a;
}

.nav-links a:nth-child(2) svg,
.mobile-bottom-nav a:nth-child(2) svg {
  color: #2563eb;
}

.nav-links a:nth-child(3) svg,
.mobile-bottom-nav a:nth-child(3) svg {
  color: #7c3aed;
}

.nav-links a:nth-child(4) svg,
.mobile-bottom-nav a:nth-child(4) svg {
  color: #c77700;
}

.nav-links a:nth-child(5) svg,
.mobile-bottom-nav a:nth-child(5) svg {
  color: #4f46e5;
}

.nav-links a:nth-child(6) svg,
.mobile-bottom-nav a:nth-child(6) svg {
  color: #c2415d;
}

.nav-links a:nth-child(7) svg,
.mobile-bottom-nav a:nth-child(7) svg {
  color: #0f8f8a;
}

.nav-links a:nth-child(8) svg,
.mobile-bottom-nav a:nth-child(8) svg {
  color: #2563eb;
}

.nav-links a.active::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 100%;
  height: 2px;
  border-radius: 0;
  background: #111313;
  transform: translateX(-50%);
}

.nav-right {
  height: 72px;
  display: flex;
  align-items: center;
  justify-self: end;
  gap: 18px;
  padding-right: 28px;
}

.nav-item-logo {
  width: 19px;
  height: 19px;
  flex: 0 0 19px;
  object-fit: contain;
}

.mobile-bottom-nav {
  display: none;
}

.icon-button,
.logout-button {
  border: 0;
  background: transparent;
  color: #697171;
  font: inherit;
  cursor: pointer;
}

.icon-button {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.icon-button:hover {
  background: #f4f6f5;
  color: #111313;
}

.user-avatar-link {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  overflow: hidden;
  background: #f2f5f4;
  text-decoration: none;
}

.user-avatar {
  width: 38px;
  height: 38px;
  border: 1px solid #dbe2df;
  border-radius: 50%;
  object-fit: cover;
}

.logout-button {
  height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #536b68;
  font-size: 15px;
  font-weight: 600;
}

.logout-button:hover {
  color: #111313;
}

@media (max-width: 768px) and (orientation: portrait) {
  .topnavbar {
    position: fixed;
    left: max(12px, env(safe-area-inset-left));
    right: max(12px, env(safe-area-inset-right));
    bottom: max(10px, env(safe-area-inset-bottom));
    z-index: 1200;
    height: 68px;
    display: block;
    border: 1px solid #dfe3e2;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.98);
    box-shadow: 0 8px 24px rgba(20, 24, 23, 0.12);
    backdrop-filter: blur(12px);
    overflow: hidden;
  }

  .brand,
  .nav-links,
  .nav-right {
    display: none;
  }

  .mobile-bottom-nav {
    height: 100%;
    display: grid;
    grid-template-columns: repeat(9, minmax(0, 1fr));
    align-items: center;
    padding: 6px;
    box-sizing: border-box;
  }

  .mobile-bottom-nav a {
    min-width: 0;
    height: 56px;
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    border-radius: 6px;
    color: #536b68;
    font-size: 11px;
    font-weight: 700;
    line-height: 1;
    text-decoration: none;
    transition:
      color 0.2s ease,
      background 0.2s ease,
      transform 0.2s ease;
  }

  .mobile-bottom-nav a span {
    width: 100%;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-bottom-nav a.active {
    color: #111313;
    background: #eef0ef;
  }

  .mobile-bottom-nav a:active {
    transform: translateY(1px);
  }
}
</style>

<style>
.topnavbar .icon-button,
.topnavbar .icon-button:hover,
.topnavbar .logout-button,
.topnavbar .logout-button:hover {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.topnavbar .logout-button {
  color: #536b68 !important;
}

.topnavbar .logout-button:hover {
  color: #111313 !important;
}
</style>
