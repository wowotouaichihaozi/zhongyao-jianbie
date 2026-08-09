import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const remoteApi = env.MOBILE_API_PROXY_TARGET || 'https://lzhan.xyz'
  const isNative = env.VITE_NATIVE_BUILD === 'true'
  const appBase = env.VITE_APP_BASE || '/m/'
  const nativeApiBase = env.VITE_API_BASE_URL || 'https://lzhan.xyz'

  if (isNative && !/^https:\/\//i.test(nativeApiBase)) {
    throw new Error('Native builds require an HTTPS VITE_API_BASE_URL.')
  }

  return {
    base: appBase,
    plugins: [
      vue(),
      VitePWA({
        disable: isNative,
        registerType: 'prompt',
        includeAssets: ['app-icon.png', 'logo.png'],
        manifest: {
          name: '嵌智学航',
          short_name: '嵌智学航',
          description: '个性化学习与多智能体资源平台',
          lang: 'zh-CN',
          start_url: '/m/',
          scope: '/m/',
          display: 'standalone',
          background_color: '#f4f7f5',
          theme_color: '#176f4b',
          icons: [
            { src: '/m/app-icon.png', sizes: '1024x1024', type: 'image/png', purpose: 'any maskable' },
          ],
        },
        workbox: {
          navigateFallback: '/m/index.html',
          navigateFallbackDenylist: [/^\/api\//, /^\/ppt-api\//],
          runtimeCaching: [],
        },
      }),
    ],
    server: {
      host: '0.0.0.0',
      port: 5090,
      strictPort: true,
      proxy: {
        '/api': { target: remoteApi, changeOrigin: true, secure: true },
        '/ppt-api': { target: remoteApi, changeOrigin: true, secure: true },
      },
    },
    preview: { port: 5091 },
    test: {
      environment: 'jsdom',
      setupFiles: './tests/setup.js',
      exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**'],
    },
  }
})
