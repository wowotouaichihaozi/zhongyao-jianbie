<script setup lang="ts">
import platformLogo from '@/assets/svg-icon/logo.svg';

defineOptions({
  name: 'GlobalLogo'
});

interface Props {
  /** Whether to show the title */
  showTitle?: boolean;
}

withDefaults(defineProps<Props>(), {
  showTitle: true
});
</script>

<template>
  <RouterLink to="/" class="w-full flex-center nowrap-hidden" aria-label="嵌智学航管理端首页">
    <img v-if="showTitle" class="platform-logo-full" :src="platformLogo" alt="嵌智学航" />
    <SystemLogo v-else class="size-32px" />
  </RouterLink>
</template>

<style scoped>
.platform-logo-full {
  width: auto;
  height: 42px;
  max-width: 164px;
  display: block;
  object-fit: contain;
}
</style>
