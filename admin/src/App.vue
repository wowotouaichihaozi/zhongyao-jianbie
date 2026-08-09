<script setup lang="ts">
import { computed } from 'vue';
import { NConfigProvider, darkTheme } from 'naive-ui';
import type { WatermarkProps } from 'naive-ui';
import { useAppStore } from './store/modules/app';
import { useThemeStore } from './store/modules/theme';
import { naiveDateLocales, naiveLocales } from './locales/naive';

defineOptions({
  name: 'App'
});

const appStore = useAppStore();
const themeStore = useThemeStore();

const naiveDarkTheme = computed(() => (themeStore.darkMode ? darkTheme : undefined));

const naiveLocale = computed(() => naiveLocales[appStore.locale]);

const naiveDateLocale = computed(() => naiveDateLocales[appStore.locale]);

const watermarkProps = computed<WatermarkProps>(() => ({
  content: themeStore.watermarkContent,
  cross: true,
  fullscreen: true,
  fontSize: 16,
  lineHeight: 16,
  width: 384,
  height: 384,
  xOffset: 12,
  yOffset: 60,
  rotate: -15,
  zIndex: 9999
}));

const clientNavItems = [
  { label: '学习画像', path: '/learning-profile', icon: 'lucide:network' },
  { label: '学习路径', path: '/learning-path', icon: 'lucide:route' },
  { label: '个性化资源', path: '/personalized-resources', icon: 'lucide:flask-conical' },
  { label: 'AI面试', path: '/digital-human-interview', icon: 'lucide:chart-no-axes-combined' },
  { label: '我的', path: '/user-profile', icon: 'lucide:user-round' }
];

function getClientHref(path: string) {
  if (typeof window === 'undefined') return path;
  if (!import.meta.env.DEV) return path;
  const { protocol, hostname } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://${hostname}:5088${path}`;
  }
  return `${protocol}//${hostname}${path}`;
}
</script>

<template>
  <NConfigProvider
    :theme="naiveDarkTheme"
    :theme-overrides="themeStore.naiveTheme"
    :locale="naiveLocale"
    :date-locale="naiveDateLocale"
    class="h-full"
  >
    <AppProvider>
      <RouterView class="bg-layout" />
      <nav class="admin-mobile-bottom-nav" aria-label="移动端平台导航">
        <a v-for="item in clientNavItems" :key="item.path" :href="getClientHref(item.path)">
          <SvgIcon class="admin-mobile-nav-icon" :icon="item.icon" />
          <span>{{ item.label }}</span>
        </a>
      </nav>
      <NWatermark v-if="themeStore.watermark.visible" v-bind="watermarkProps" />
    </AppProvider>
  </NConfigProvider>
</template>

<style scoped>
.admin-mobile-bottom-nav {
  display: none;
}

@media (max-width: 768px) and (orientation: portrait) {
  .admin-mobile-bottom-nav {
    position: fixed;
    left: max(12px, env(safe-area-inset-left));
    right: max(12px, env(safe-area-inset-right));
    bottom: max(10px, env(safe-area-inset-bottom));
    z-index: 10000;
    height: 70px;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 4px;
    padding: 6px;
    border: 1px solid rgba(16, 185, 129, 0.18);
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.95);
    box-shadow: 0 16px 36px rgba(15, 118, 110, 0.18);
    backdrop-filter: blur(18px);
  }

  .admin-mobile-bottom-nav a {
    min-width: 0;
    min-height: 56px;
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    border-radius: 18px;
    color: #536b68;
    font-size: 11px;
    font-weight: 700;
    line-height: 1;
    text-decoration: none;
    -webkit-tap-highlight-color: transparent;
  }

  .admin-mobile-bottom-nav a:active,
  .admin-mobile-bottom-nav a:first-child {
    color: #10a66f;
    background: linear-gradient(180deg, #e6fbf1 0%, #f3fffa 100%);
  }

  .admin-mobile-nav-icon {
    font-size: 21px;
  }
}
</style>

<style>
@media (max-width: 768px) and (orientation: portrait) {
  .bg-layout {
    padding-bottom: calc(96px + env(safe-area-inset-bottom));
    box-sizing: border-box;
  }
}
</style>
