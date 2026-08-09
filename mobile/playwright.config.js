import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:5090/m/', trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1',
    url: 'http://127.0.0.1:5090/m/',
    reuseExistingServer: true,
  },
  projects: [
    { name: 'mobile-390', use: { ...devices['iPhone 13'], browserName: 'chromium', viewport: { width: 390, height: 844 } } },
    { name: 'mobile-360', use: { ...devices['Galaxy S9+'], browserName: 'chromium', viewport: { width: 360, height: 800 } } },
    { name: 'mobile-430', use: { ...devices['iPhone 13'], browserName: 'chromium', viewport: { width: 430, height: 932 } } },
    { name: 'mobile-landscape', use: { ...devices['iPhone 13'], browserName: 'chromium', viewport: { width: 844, height: 390 } } },
    { name: 'tablet-768', use: { ...devices['iPad Mini'], browserName: 'chromium', viewport: { width: 768, height: 1024 } } },
  ],
})
