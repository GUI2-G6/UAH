import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './test/playwright',
  timeout: 30000,
  use: {
    headless: true,
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
})
