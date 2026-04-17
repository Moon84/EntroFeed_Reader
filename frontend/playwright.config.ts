import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:8001',
    headless: true,
  },
  webServer: {
    command: 'cd .. && ENTROFEED_STORAGE_HANDLER=sqlite .venv/bin/uvicorn src.app:app --port 8001',
    port: 8001,
    timeout: 60000,
    reuseExistingServer: true,
  },
})
