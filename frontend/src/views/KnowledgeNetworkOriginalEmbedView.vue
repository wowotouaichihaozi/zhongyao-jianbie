<template>
  <main class="knowledge-network-original-page">
    <iframe
      class="knowledge-network-original"
      src="/wu-xing-holo-core-original/index.html?v=20260829-nav3"
      title="Wu Xing Holo-Core"
    ></iframe>
  </main>
</template>

<style scoped>
.knowledge-network-original-page {
  position: relative;
  width: 100%;
  height: calc(100vh - 72px);
  height: calc(100dvh - 72px);
  min-height: 0;
  overflow: hidden;
  background: #020306;
}

.knowledge-network-original {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}

@media (max-width: 768px) and (orientation: portrait) {
  .knowledge-network-original-page {
    height: calc(100vh - 88px);
    height: calc(100dvh - 88px);
  }
}
</style>

<style>
body:has(.knowledge-network-original-page) {
  overflow: hidden;
}
</style>
