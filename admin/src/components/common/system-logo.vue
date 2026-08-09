<script setup lang="ts">
import platformLogo from '@/assets/svg-icon/logo.svg';
</script>

<template>
  <div class="app-logo" aria-hidden="true">
    <img :src="platformLogo" alt="" />
  </div>
</template>

<style scoped>
.app-logo {
  overflow: hidden;
}

.app-logo img {
  width: auto;
  max-width: none;
  height: 100%;
  display: block;
}
</style>
